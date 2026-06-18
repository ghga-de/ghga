from math import exp


def test_config(rendered_chart, expected, release_name):
    manifests = rendered_chart("common.yaml", "config.yaml")
    assert manifests["ConfigMap"]["data"]["config"] == expected("config", "configMap")["data"]
    assert manifests["ConfigMap"]["metadata"]["name"] == f"{release_name}"
    volume = manifests["Deployment"]["spec"]["template"]["spec"]["volumes"][0]
    assert volume == expected("config", "volume")

    mount = manifests["Deployment"]["spec"]["template"]["spec"]["containers"][0]["volumeMounts"][0]
    assert mount == expected("config", "mount")



def test_extra_volume(rendered_chart):
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
    manifests = rendered_chart()
    assert "KafkaUser" not in manifests
    manifests = rendered_chart("kafka_user.yaml")
    assert (
        expected("kafka_user", "acls")
        == manifests["KafkaUser"]["spec"]["authorization"]["acls"]
    )
    assert (
        expected("kafka_user", "secretAnnotations").items()
        <= manifests["KafkaUser"]["spec"]["template"]["secret"]["metadata"]["annotations"].items()
    )


def test_vault_agent(rendered_chart, release_name, expected):
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

    command = manifests["Deployment"]["spec"]["template"]["spec"]["containers"][0]["command"]
    args = manifests["Deployment"]["spec"]["template"]["spec"]["containers"][0]["args"]
    assert command == expected("vault_enabled", "command")
    assert args == expected("vault_enabled", "args")
    

def test_vault_boilerplate_extra_annotations(rendered_chart, release_name, expected):
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

    command = manifests["Deployment"]["spec"]["template"]["spec"]["containers"][0]["command"]
    args = manifests["Deployment"]["spec"]["template"]["spec"]["containers"][0]["args"]
    assert command == expected("vault_boilerplate", "command")
    assert args == expected("vault_boilerplate", "args")


def test_vault_boilerplate_omits_unset_annotations(rendered_chart):
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

    command = manifests["Deployment"]["spec"]["template"]["spec"]["containers"][0]["command"]
    args = manifests["Deployment"]["spec"]["template"]["spec"]["containers"][0]["args"]
    assert command == expected("vault_single_template", "command")
    assert args == expected("vault_single_template", "args")
    