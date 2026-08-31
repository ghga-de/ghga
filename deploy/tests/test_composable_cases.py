"""Composable render cases for the ghga-common library chart."""


def test_common_labels_reach_every_resource_service_labels_stay_scoped(rendered_chart):
    """commonLabels/commonAnnotations land on every rendered resource - there is no
    separate, narrower per-workload-only labels/annotations value anymore. service.
    labels/service.annotations are the deliberate exception: Service-only (and
    DestinationRule, which shares its address), not merged into anything else.
    """
    manifests = rendered_chart("common.yaml", "common_and_service_labels.yaml")

    for kind in ("Deployment", "Service", "ConfigMap", "ServiceAccount"):
        meta = manifests[kind]["metadata"]
        assert meta["labels"]["team"] == "archive"
        assert meta["annotations"]["common-ann"] == "common-value"

    service_meta = manifests["Service"]["metadata"]
    assert service_meta["labels"]["svc-only"] == "svc-label-value"
    assert service_meta["annotations"]["svc-ann"] == "svc-ann-value"

    for kind in ("Deployment", "ConfigMap", "ServiceAccount"):
        meta = manifests[kind]["metadata"]
        assert "svc-only" not in meta["labels"]
        assert "svc-ann" not in meta.get("annotations", {})


def test_pull_secrets_combine_global_and_image(rendered_chart):
    """global.imagePullSecrets and image.pullSecrets both land on imagePullSecrets,
    routed through the vendored common.images.renderPullSecrets helper - not the
    unrelated, undocumented top-level `imagePullSecrets` value the Deployment/Job/
    CronJob templates used to hand-roll a check against instead.
    """
    manifests = rendered_chart("common.yaml", "pull_secrets.yaml")
    secrets = manifests["Deployment"]["spec"]["template"]["spec"]["imagePullSecrets"]
    assert sorted(s["name"] for s in secrets) == ["from-global", "from-image"]


def test_config(rendered_chart, expected, release_name):
    """Config map, volume and mount render from the config values."""
    manifests = rendered_chart("common.yaml", "config.yaml")
    assert (
        manifests["ConfigMap"]["data"]["config"]
        == expected("config", "configMap")["data"]
    )
    assert manifests["ConfigMap"]["metadata"]["name"] == f"{release_name}"
    volume = manifests["Deployment"]["spec"]["template"]["spec"]["volumes"][0]
    assert volume == expected("config", "volume")

    mount = manifests["Deployment"]["spec"]["template"]["spec"]["containers"][0][
        "volumeMounts"
    ][0]
    assert mount == expected("config", "mount")


def test_extra_volume(rendered_chart):
    """Extra volumes reach deployments and cronjobs alike."""
    manifests = rendered_chart("extra_volume.yaml")
    assert (
        "test"
        == manifests["Deployment"]["spec"]["template"]["spec"]["volumes"][1]["name"]
    )
    assert (
        "test"
        == manifests["CronJob"]["spec"]["jobTemplate"]["spec"]["template"]["spec"][
            "volumes"
        ][1]["name"]
    )


def test_kafka_user(rendered_chart, expected):
    """KafkaUser renders only when enabled, with ACLs and annotations."""
    manifests = rendered_chart()
    assert "KafkaUser" not in manifests
    manifests = rendered_chart("kafka_user.yaml")
    assert (
        expected("kafka_user", "acls")
        == manifests["KafkaUser"]["spec"]["authorization"]["acls"]
    )
    assert (
        expected("kafka_user", "secretAnnotations").items()
        <= manifests["KafkaUser"]["spec"]["template"]["secret"]["metadata"][
            "annotations"
        ].items()
    )


def test_vault_agent(rendered_chart, release_name, expected):
    """Vault agent annotations and command wrapper render when enabled."""
    manifests = rendered_chart("common.yaml", "vault_enabled.yaml")
    exp = expected("vault_enabled", "podAnnotations")
    got = manifests["Deployment"]["spec"]["template"]["metadata"]["annotations"]

    diff = {k: (v, got.get(k)) for k, v in exp.items() if got.get(k) != v}
    print(diff)
    assert not diff, diff

    assert (
        expected("vault_enabled", "podAnnotations").items()
        <= manifests["Deployment"]["spec"]["template"]["metadata"][
            "annotations"
        ].items()
    )

    command = manifests["Deployment"]["spec"]["template"]["spec"]["containers"][0][
        "command"
    ]
    args = manifests["Deployment"]["spec"]["template"]["spec"]["containers"][0]["args"]
    assert command == expected("vault_enabled", "command")
    assert args == expected("vault_enabled", "args")


def test_vault_boilerplate_extra_annotations(rendered_chart, release_name, expected):
    """Extra vault annotations merge into the boilerplate."""
    manifests = rendered_chart("common.yaml", "vault_boilerplate.yaml")
    exp = expected("vault_boilerplate", "podAnnotations")
    got = manifests["Deployment"]["spec"]["template"]["metadata"]["annotations"]

    diff = {k: (v, got.get(k)) for k, v in exp.items() if got.get(k) != v}
    print(diff)
    assert not diff, diff

    assert (
        expected("vault_boilerplate", "podAnnotations").items()
        <= manifests["Deployment"]["spec"]["template"]["metadata"][
            "annotations"
        ].items()
    )

    command = manifests["Deployment"]["spec"]["template"]["spec"]["containers"][0][
        "command"
    ]
    args = manifests["Deployment"]["spec"]["template"]["spec"]["containers"][0]["args"]
    assert command == expected("vault_boilerplate", "command")
    assert args == expected("vault_boilerplate", "args")


def test_vault_boilerplate_omits_unset_annotations(rendered_chart):
    """Unset vault annotations stay absent."""
    manifests = rendered_chart("common.yaml", "vault_enabled.yaml")
    annotations = manifests["Deployment"]["spec"]["template"]["metadata"]["annotations"]

    for key in (
        "vault.hashicorp.com/ca-cert",
        "vault.hashicorp.com/tls-secret",
        "vault.hashicorp.com/service",
        "vault.hashicorp.com/tls-server-name",
    ):
        assert key not in annotations


def test_vault_single_template(rendered_chart, release_name, expected):
    """Single-template vault mode renders exec-style command."""
    manifests = rendered_chart("common.yaml", "vault_single_template.yaml")
    exp = expected("vault_single_template", "podAnnotations")
    got = manifests["Deployment"]["spec"]["template"]["metadata"]["annotations"]

    diff = {k: (v, got.get(k)) for k, v in exp.items() if got.get(k) != v}
    print(diff)
    assert not diff, diff

    assert (
        expected("vault_single_template", "podAnnotations").items()
        <= manifests["Deployment"]["spec"]["template"]["metadata"][
            "annotations"
        ].items()
    )

    command = manifests["Deployment"]["spec"]["template"]["spec"]["containers"][0][
        "command"
    ]
    args = manifests["Deployment"]["spec"]["template"]["spec"]["containers"][0]["args"]
    assert command == expected("vault_single_template", "command")
    assert args == expected("vault_single_template", "args")


def test_http_route(rendered_chart):
    """HTTPRoute renders the default rule; extra keys pass into spec."""
    manifests = rendered_chart()
    assert "HTTPRoute" not in manifests

    # minimal shape: spec holds only the default rule (regression check: an empty
    # leftover of the httpRoute values used to render a bare `{}` into spec)
    manifests = rendered_chart("http_route.yaml")
    spec = manifests["HTTPRoute"]["spec"]
    assert set(spec) == {"rules"}
    rule = spec["rules"][0]
    assert rule["backendRefs"][0]["port"] == 8080
    assert rule["matches"][0]["path"]["value"] == "/api/test"

    # extra httpRoute keys pass through into spec
    manifests = rendered_chart("http_route.yaml", "http_route_parent_refs.yaml")
    assert manifests["HTTPRoute"]["spec"]["parentRefs"] == [{"name": "ghga-gateway"}]

    # rewritePath=false forwards the full path (services that build their own URLs)
    manifests = rendered_chart("http_route.yaml", "http_route_no_rewrite.yaml")
    rule = manifests["HTTPRoute"]["spec"]["rules"][0]
    assert "filters" not in rule
    assert rule["matches"][0]["path"]["value"] == "/api/test"

    # a root base path ("/") must not collapse to an empty match (SPA routes)
    manifests = rendered_chart("http_route_root.yaml")
    rule = manifests["HTTPRoute"]["spec"]["rules"][0]
    assert rule["matches"][0]["path"]["value"] == "/"


def test_container_ports_drive_service_and_networkpolicy(rendered_chart):
    """ContainerPorts is the single source for the Deployment/Service/NetworkPolicy
    ports - not three independent values that could drift out of sync. Covers both
    the bare-number form (protocol defaults to TCP) and the {port, protocol} form.
    """
    manifests = rendered_chart("common.yaml", "custom_container_ports.yaml")

    container = manifests["Deployment"]["spec"]["template"]["spec"]["containers"][0]
    assert sorted(container["ports"], key=lambda p: p["name"]) == [
        {"name": "dns", "containerPort": 53, "protocol": "UDP"},
        {"name": "http", "containerPort": 8080, "protocol": "TCP"},
    ]

    assert sorted(manifests["Service"]["spec"]["ports"], key=lambda p: p["name"]) == [
        {"name": "dns", "protocol": "UDP", "port": 53, "targetPort": "dns"},
        {"name": "http", "protocol": "TCP", "port": 8080, "targetPort": "http"},
    ]

    assert sorted(
        manifests["NetworkPolicy"]["spec"]["ingress"][0]["ports"],
        key=lambda p: p["port"],
    ) == [
        {"port": 53, "protocol": "UDP"},
        {"port": 8080, "protocol": "TCP"},
    ]


def test_no_container_ports_renders_no_ports_anywhere(rendered_chart):
    """An empty containerPorts list turns off ports on all three resources."""
    manifests = rendered_chart("common.yaml", "no_container_ports.yaml")

    container = manifests["Deployment"]["spec"]["template"]["spec"]["containers"][0]
    assert "ports" not in container
    assert "ports" not in manifests["Service"]["spec"]
    assert "ports" not in manifests["NetworkPolicy"]["spec"]["ingress"][0]


def test_command_style_exec(rendered_chart):
    """commandStyle=exec renders a real argv without a shell."""
    # shell style (default): command is the shell wrapper, args one joined string
    manifests = rendered_chart("common.yaml")
    container = manifests["Deployment"]["spec"]["template"]["spec"]["containers"][0]
    assert container["command"] == ["sh", "-c"]

    # exec style: real argv, no shell involved (shell-less hardened images)
    manifests = rendered_chart("common.yaml", "command_style_exec.yaml")
    container = manifests["Deployment"]["spec"]["template"]["spec"]["containers"][0]
    assert container["command"] == ["myexe"]
    assert container["args"] == ["run-rest"]


def test_cronjob_single_backward_compatible(rendered_chart, expected):
    """A single, unnamed cronjobs[] entry keeps the pre-array naming (no suffix).

    and inherits schedule/command/history-limit from the top-level values.
    """
    manifests = rendered_chart("common.yaml", "cronjob_single.yaml")

    assert "Deployment" not in manifests

    cronjob = manifests["CronJob"]
    assert cronjob["metadata"]["name"] == expected("cronjob_single", "metadata")["name"]
    assert cronjob["spec"]["schedule"] == expected("cronjob_single", "spec")["schedule"]
    assert (
        cronjob["spec"]["successfulJobsHistoryLimit"]
        == expected("cronjob_single", "spec")["successfulJobsHistoryLimit"]
    )

    container = cronjob["spec"]["jobTemplate"]["spec"]["template"]["spec"][
        "containers"
    ][0]
    assert container["command"] == expected("cronjob_single", "command")
    assert container["args"] == expected("cronjob_single", "args")


def test_cronjobs_multiple_with_overrides(rendered_objects, expected):
    """Deployment and multiple cronjobs can be shipped side by side; each cronjob.

    entry can override its own schedule/history-limit/entrypoint/resources, an
    entry with `enabled: false` is skipped, and entries without overrides fall
    back to the top-level values (same as the Deployment uses).
    """
    objects = rendered_objects("common.yaml", "cronjobs_multiple.yaml")

    deployment_expected = expected("cronjobs_multiple", "deployment")
    deployments = [obj for obj in objects if obj["kind"] == "Deployment"]
    assert len(deployments) == 1
    deployment = deployments[0]
    assert deployment["metadata"]["name"] == deployment_expected["name"]

    deployment_container = deployment["spec"]["template"]["spec"]["containers"][0]
    assert deployment_container["command"] == deployment_expected["command"]
    assert deployment_container["args"] == deployment_expected["args"]

    cronjobs = {
        obj["metadata"]["name"]: obj for obj in objects if obj["kind"] == "CronJob"
    }
    cleanup_expected = expected("cronjobs_multiple", "cleanup")
    report_expected = expected("cronjobs_multiple", "report")
    assert set(cronjobs) == {cleanup_expected["name"], report_expected["name"]}

    for exp in (cleanup_expected, report_expected):
        job = cronjobs[exp["name"]]
        assert job["spec"]["schedule"] == exp["schedule"]
        assert (
            job["spec"]["successfulJobsHistoryLimit"]
            == exp["successfulJobsHistoryLimit"]
        )
        container = job["spec"]["jobTemplate"]["spec"]["template"]["spec"][
            "containers"
        ][0]
        assert container["name"] == exp["containerName"]
        assert container["command"] == exp["command"]
        assert container["args"] == exp["args"]
        assert container["resources"] == exp["resources"]


def test_cronjob_pod_annotations_override(rendered_objects, expected):
    """A cronjob entry can add/override pod annotations (e.g. to run the vault.

    agent as an init-only container for a short-lived Job) without affecting
    the Deployment or other cronjobs, which keep the shared/vault annotations.
    """
    objects = rendered_objects(
        "common.yaml", "vault_enabled.yaml", "cronjob_pod_annotations.yaml"
    )

    deployment = next(obj for obj in objects if obj["kind"] == "Deployment")
    deployment_annotations = deployment["spec"]["template"]["metadata"]["annotations"]
    deployment_expected = expected("cronjob_pod_annotations", "deployment")
    assert (
        deployment_annotations["vault.hashicorp.com/agent-pre-populate-only"]
        == deployment_expected["agentPrePopulateOnly"]
    )
    assert "backup.example.com/note" not in deployment_annotations

    cronjob = next(obj for obj in objects if obj["kind"] == "CronJob")
    cronjob_annotations = cronjob["spec"]["jobTemplate"]["spec"]["template"][
        "metadata"
    ]["annotations"]
    cronjob_expected = expected("cronjob_pod_annotations", "cronjob")
    assert (
        cronjob_annotations["vault.hashicorp.com/agent-pre-populate-only"]
        == cronjob_expected["agentPrePopulateOnly"]
    )
    assert cronjob_annotations["backup.example.com/note"] == cronjob_expected["note"]


def test_cronjob_pod_annotations_override_no_duplicate_key(rendered_text):
    """Regression test: annotations used to be built by concatenating three raw YAML.

    blocks (top-level podAnnotations, vaultAgent-generated annotations, per-cronjob
    podAnnotations) with no deduplication. A cronjob overriding a key the vaultAgent
    block already sets (e.g. agent-pre-populate-only, to run a one-shot job without
    the agent as a long-lived sidecar) produced a literal duplicate YAML key. That
    happened to "work" under yaml.safe_load (last occurrence wins) but is invalid
    under stricter YAML consumers, so assert directly against the rendered text.
    """
    text = rendered_text(
        "common.yaml", "vault_enabled.yaml", "cronjob_pod_annotations.yaml"
    )
    cronjob_section = text.split("kind: CronJob", 1)[1]
    assert cronjob_section.count("vault.hashicorp.com/agent-pre-populate-only:") == 1


def test_vault_single_template_applies_to_job_and_cronjob(rendered_chart, expected):
    """SingleTemplate mode must fold vault secrets into one combined annotation set for.

    every workload kind (Deployment, Job, CronJob), not just the Deployment. Job and
    CronJob previously always used the old per-secret annotations regardless of the
    singleTemplate flag, while the command/args template dropped the vault-secrets
    sourcing wrapper for *every* kind once singleTemplate was set -- silently leaving
    Job/CronJob with no way to load their secrets at all.
    """
    manifests = rendered_chart(
        "common.yaml",
        "vault_single_template.yaml",
        "vault_single_template_cronjob.yaml",
    )

    deployment_annotations = manifests["Deployment"]["spec"]["template"]["metadata"][
        "annotations"
    ]
    deployment_command = manifests["Deployment"]["spec"]["template"]["spec"][
        "containers"
    ][0]["command"]
    deployment_args = manifests["Deployment"]["spec"]["template"]["spec"]["containers"][
        0
    ]["args"]

    exp = expected("vault_single_template", "podAnnotations")
    assert exp.items() <= deployment_annotations.items()
    assert deployment_command == expected("vault_single_template", "command")
    assert deployment_args == expected("vault_single_template", "args")

    def strip(annotations):
        return {
            k: v
            for k, v in annotations.items()
            if k not in ("helm.sh/revision", "configmap-hash")
        }

    job = manifests["Job"]
    job_container = job["spec"]["template"]["spec"]["containers"][0]
    assert strip(job["spec"]["template"]["metadata"]["annotations"]) == strip(
        deployment_annotations
    )
    assert job_container["command"] == deployment_command
    assert job_container["args"] == deployment_args

    cronjob = manifests["CronJob"]
    cronjob_container = cronjob["spec"]["jobTemplate"]["spec"]["template"]["spec"][
        "containers"
    ][0]
    cronjob_annotations = cronjob["spec"]["jobTemplate"]["spec"]["template"][
        "metadata"
    ]["annotations"]
    assert strip(cronjob_annotations) == strip(deployment_annotations)
    assert cronjob_container["command"] == deployment_command
    assert cronjob_container["args"] == deployment_args
