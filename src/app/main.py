# SPDX-License-Identifier: Apache-2.0

"""Workflow Engine main file."""

import io
import json
import os
import sys
import zipfile
from configparser import BasicInterpolation, ConfigParser
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from threading import Thread
from urllib.parse import urlparse, urlunparse

import luigi.server
import sh
import tornado.web

# from entitysdk.models.workflow import WorkflowExecution
from sh import ErrorReturnCode
from tornado.httpclient import AsyncHTTPClient

from app import hpc_resource
from app.common import ProjectContext
from app.config import auth_client, settings
from app.exception import ClusterError
from app.logger import L


def _zip_files(files, cfg_name):
    """Zip files from POST request and extract nexus info from cfg name.

    Returns:
        Zip file buffer and nexus instance, org, proj.
    """
    buf = io.BytesIO()
    kg_params = {}
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for _, values in files.items():
            for file_ in values:
                archive.writestr(file_["filename"], file_["body"])
                if file_["filename"] == cfg_name:
                    cfg = ConfigParser(interpolation=BasicInterpolation())
                    cfg.read_string(file_["body"].decode())
                    kg_params |= {
                        "NEXUS_BASE": cfg.get(
                            "DEFAULT", "kg-base", fallback=os.getenv("NEXUS_BASE")
                        ),
                        "NEXUS_ORG": cfg.get("DEFAULT", "kg-org", fallback=os.getenv("NEXUS_ORG")),
                        "NEXUS_PROJ": cfg.get("DEFAULT", "kg-proj", fallback=None),
                        "NEXUS_NO_PROV": cfg.get("DEFAULT", "kg-no-prov", fallback=None),
                    }
    buf.seek(0)
    return buf, kg_params


def _dump_files(buf, dest: Path) -> None:
    """Write zipped files from buf to dest."""
    with zipfile.ZipFile(buf, mode="r") as archive:
        archive.extractall(dest)
    buf.seek(0)


def _register_workflow(
    *,
    buffer_or_path,
    env,
    timestamp,
    module,
    task,
    cfg_name,
    project_context,
):
    # pylint: disable=too-many-positional-arguments):
    """Register workflow execution in nexus."""
    # zip_name = f"{timestamp}.zip"

    # The environment must always hold the initial access token we received because it is used
    # as a key to track the updated tokens in auth sidecar service
    # access_token = auth_client.refresh_token(
    #     access_token=env["ACCESS_TOKEN"],
    # )

    # buffer_or_path.seek(0)
    """
    file_to_upload = FileToUpload(
        filename=zip_name,
        content_type="application/zip",
        buffer_or_path=buffer_or_path,
    )
    entity = WorkflowExecution(
        name=f"{module}.{task}",
        description=f"{module}.{task}",
        module=module,
        task=task,
        version=VERSION,
        configFileName=cfg_name,
        status="Running",
        startedAtTime=datetime.utcnow(),
    )
    registered = register_entity(
        entity=entity,
        files_to_upload=[file_to_upload],
        project_context=project_context,
        token=token,
    )
    """
    # return str(registered.id), registered.url
    return ("0", "foo")


def _register_workflow_provenance(
    *,
    buffer_or_path,
    env,
    timestamp,
    module,
    task,
    cfg_name,
    project_context,
):
    # pylint: disable=too-many-positional-arguments
    """Register workflow execution entity and update env with the link to it."""
    if "NEXUS_NO_PROV" in env:
        L.warning("Workflow provenance will not be registered!")
        return None

    L.debug("Registering workflow provenance...")

    id_, url = _register_workflow(
        buffer_or_path=buffer_or_path,
        env=env,
        timestamp=timestamp,
        module=module,
        task=task,
        cfg_name=cfg_name,
        project_context=project_context,
    )
    L.info("WORKFLOW LINK: %s", url)
    return id_


def _update_workflow_status(*, workflow_id, env, status):
    if workflow_id:
        """
        if "KC_REFRESH_TOKEN" in env and env["KC_REFRESH_TOKEN"]:
            token = KEYCLOAK.refresh_token(env["KC_REFRESH_TOKEN"])["access_token"]
        else:
            token = env["KC_ACCESS_TOKEN"]

        workflow = update_entity(
            hpc_resource_id=workflow_id,
            model=WorkflowExecution,
            attributes_to_update={
                "status": status,
                "endedAtTime": datetime.utcnow(),
            },
            project_context=ProjectContext(
                project_id=env["PROJECT_ID"],
                virtual_lab_id=env["VIRTUAL_LAB_ID"],
            ),
            token=token,
        )
        """
        workflow_id = None
        L.info("Workflow %s is updated with status %s", workflow_id, status)
    else:
        L.info("No workflow id to update. Workflow status: %s", status)


def _run_worker(cmd_params, env):
    workflow_id = env.get("NEXUS_WORKFLOW", None)

    try:
        cluster_login_info = hpc_resource.request_cluster_and_wait(
            api_url=settings.hpc_resource_provisioner_api_url,
            cluster_id=hpc_resource.ClusterID(
                project=env["PROJECT_ID"],
                virtual_lab=env["VIRTUAL_LAB_ID"],
            ),
        )
    except ClusterError as e:
        _update_workflow_status(
            env=env,
            status="Failed",
            workflow_id=workflow_id,
        )
        raise RuntimeError("Cluster failed to be provisioned for task.") from e

    key = cluster_login_info.ssh_key
    new_env = env.copy()
    new_env["HPC_HEAD_NODE"] = cluster_login_info.head_node_ip

    try:
        with _ssh_agt(key) as ssh_auth_sock:
            sh.luigi(*cmd_params, _env=new_env | ssh_auth_sock, _out=sys.stdout, _err=sys.stderr)
        _update_workflow_status(workflow_id=workflow_id, env=env, status="Done")
    except ErrorReturnCode:
        _update_workflow_status(workflow_id=workflow_id, env=env, status="Failed")
        raise


def _launch(*, buf, env, timestamp, module_name, task_name, project_context, cfg_name):
    # pylint: disable=too-many-positional-arguments
    """Launch the luigi task."""
    workflow_id = _register_workflow_provenance(
        buffer_or_path=buf,
        env=env,
        timestamp=timestamp,
        module=module_name,
        task=task_name,
        cfg_name=cfg_name,
        project_context=project_context,
    )

    if workflow_id:
        env["NEXUS_WORKFLOW"] = workflow_id

    workflows_path = settings.workflows_path / timestamp

    _dump_files(buf, workflows_path)
    env["PYTHONPATH"] = str(workflows_path)

    if cfg_name:
        L.info("Copied config file to: %s", workflows_path / cfg_name)
        env["LUIGI_CONFIG_PATH"] = str(workflows_path / cfg_name)

    cmd_params = [
        "--logging-conf-file",
        settings.logging_cfg_path,
        "--module",
        module_name,
        task_name,
    ]

    L.info("Launching: %s", cmd_params)

    Thread(target=_run_worker, args=(cmd_params, env)).start()

    return workflow_id


class VersionHandler(tornado.web.RequestHandler):
    """Handle version requests."""

    # pylint: disable=abstract-method

    def get(self, *_, **__):
        """Get version."""
        # assert SESSION_ID == self.get_cookie("sessionid")
        self.write(settings.app_version)


class HealthzHandler(tornado.web.RequestHandler):
    """Handle healthz requests."""

    # pylint: disable=abstract-method

    def get(self, *_, **__):
        """Get."""
        self.set_status(204)


class TagsHandler(tornado.web.RequestHandler):
    """Handle task id requests."""

    # pylint: disable=abstract-method

    def get(self, *_, **__):
        """Get."""
        self.write(
            {
                "virtual_lab": settings.VIRTUAL_LAB_ID,
                "project": settings.PROJECT_ID,
            }
        )


class DashboardHandler(tornado.web.RequestHandler):
    """Proxy luigi dashboard."""

    # pylint: disable=abstract-method

    async def get(self, *_, **__):
        """Get."""
        client = AsyncHTTPClient()
        url = self.request.uri
        parsed_url = urlparse(url)
        if parsed_url.path == "/dashboard/":
            path = "/static/visualiser/index.html"
        else:
            path = parsed_url.path.replace("/dashboard/", "/static/visualiser/")
        url = urlunparse(
            (
                "http",
                "127.0.0.1:8082",
                path,
                parsed_url.params,
                parsed_url.query,
                parsed_url.fragment,
            )
        )
        response = await client.fetch(url)
        self.set_status(response.code, response.reason)
        for header, v in response.headers.get_all():
            if header not in (
                "Content-Length",
                "Transfer-Encoding",
                "Content-Encoding",
                "Connection",
            ):
                self.add_header(header, v)

        if response.body:
            self.set_header("Content-Length", len(response.body))
            self.write(response.body)
        self.finish()


@contextmanager
def _ssh_agt(key):
    """Will update env with SSH_AUTH_SOCK value."""
    ssh_agent_proc = sh.ssh_agent("-D", _bg=True, _iter=True, _ok_code=[0, 2])
    line = next(ssh_agent_proc, None)
    env = os.environ.copy()
    ssh_auth_sock = dict([line.split(";")[0].split("=")])  # put ssh_auth_sock var into env
    env |= ssh_auth_sock
    sh.ssh_add("-", _env=env, _in=key, _out=sys.stdout, _err=sys.stderr)
    try:
        yield ssh_auth_sock
    finally:
        if ssh_agent_proc.is_alive():
            ssh_agent_proc.terminate()
        for _ in ssh_agent_proc:  # drain output
            pass


class ApiLaunchHandler(tornado.web.RequestHandler):
    """Launch task through API."""

    # pylint: disable=abstract-method

    def post(self, task):
        """Handle post."""
        # if SESSION_ID != self.get_cookie("sessionid"):
        #    self.set_status(403)
        #    return
        L.info("API launch: %s", task)

        access_token = self.request.headers.get("Authorization").replace("Bearer ", "")
        refresh_token = self.get_body_argument("refresh-token")

        # register tokens in auth service
        auth_client.register_tokens(
            access_token=access_token,
            refresh_token=refresh_token,
        )

        env = {
            "KEYCLOAK_ACCESS_TOKEN": access_token,
        }
        if settings.debug:
            env |= {"DEBUG": "True"}

        # e.g. bbp_workflow.sbo.sim.task, RunSimCampaignMeta
        module_name, task_name = task.rsplit(".", 1)
        L.info("Module name: %s, Task name: %s", module_name, task_name)

        cfg_name = self.get_body_argument("cfg_name", None)
        L.info("Config name: %s", cfg_name)

        timestamp = f"{datetime.now():%Y-%m-%d_%H-%M-%S.%f}"

        # FIXME
        buf, kg_params = _zip_files(self.request.files, cfg_name)

        env |= {k: v for k, v in kg_params.items() if v is not None}

        project_id = self.request.headers.get("project-id")
        virtual_lab_id = self.request.headers.get("virtual-lab-id")

        project_context = ProjectContext(
            project_id=project_id,
            virtual_lab_id=virtual_lab_id,
        )

        if project_id != settings.project_id or virtual_lab_id != settings.virtual_lab_id:
            raise RuntimeError(
                f"Project or virtual lab received from the request does not match the instance's "
                f"project or virtual lab. "
                f"project: {project_id}, virtual_lab: {virtual_lab_id}\n"
                f"PROJECT: {settings.PROJECT_ID}, VIRTUAL_LAB: {settings.VIRTUAL_LAB_ID}"
            )

        env["PROJECT_ID"] = project_id
        env["VIRTUAL_LAB_ID"] = virtual_lab_id

        print("buf", buf)  # TODO: Remove when done
        print("env", env)  # TODO: Remove when done

        workflow_execution_id = _launch(
            buf=buf,
            env=env,
            project_context=project_context,
            timestamp=timestamp,
            module_name=module_name,
            task_name=task_name,
            cfg_name=cfg_name,
        )
        if workflow_execution_id:
            self.write(str(workflow_execution_id))
        self.set_status(200)


async def idle_culling(call_later_fn):
    """Stop if idle."""
    # check worker_list for idle culling
    client = AsyncHTTPClient()
    try:
        response = await client.fetch("http://127.0.0.1:8082/api/worker_list")
        worker_list = json.loads(response.body)["response"]
        L.info("Worker list: %s", worker_list)
        if not worker_list:
            luigi.server.stop()
        call_later_fn(settings.idle_timeout, idle_culling, call_later_fn)
    except Exception:  # pylint: disable=broad-except
        luigi.server.stop()


def main(host, port):
    """Start the workflow launcher."""
    app = tornado.web.Application(
        [
            (r"/launch/([^/]+)/", ApiLaunchHandler),
            ("/dashboard/.*", DashboardHandler),
            ("/api/.*", DashboardHandler),
            ("/version/", VersionHandler),
            ("/healthz/", HealthzHandler),
            ("/tags/", TagsHandler),
        ],
    )
    app.listen(port, address=host)

    call_later_fn = tornado.ioloop.IOLoop.current().call_later
    call_later_fn(settings.idle_timeout, idle_culling, call_later_fn)

    luigi.server.run(address="127.0.0.1")
