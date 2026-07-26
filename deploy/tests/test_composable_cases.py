"""Composable render cases for the ghga-common library chart."""


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
