def test_config(rendered_chart):
    manifests = rendered_chart("common.yaml", "config.yaml")
    assert manifests["ConfigMap"]["data"]["config"] == "foo: bar\n"
    print(manifests["ConfigMap"]["data"]["config"])


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
    manifests = rendered_chart("vault_enabled.yaml")
    assert (
        expected("vault_enabled", "podAnnotations").items()
        <= manifests["Deployment"]["spec"]["template"]["metadata"][
            "annotations"
        ].items()
    )
