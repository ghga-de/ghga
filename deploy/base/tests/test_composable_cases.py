def test_config(rendered_chart):
    manifests = rendered_chart("common.yaml", "config.yaml")
    assert manifests["ConfigMap"]["data"]["config"] == "foo: bar\n"
    print(manifests["ConfigMap"]["data"]["config"])

def test_extra_volume(rendered_chart):
    manifests = rendered_chart("extra_volume.yaml")
    assert "test" == manifests["Deployment"]["spec"]["template"]["spec"]["volumes"][1]["name"]
    assert "test" == manifests["CronJob"]["spec"]["jobTemplate"]["spec"]["template"]["spec"]["volumes"][1]["name"]

def test_kafka_user(rendered_chart):
    manifests = rendered_chart()
    assert "KafkaUser" not in manifests
    manifests = rendered_chart("kafka_user.yaml")
    expected_acl = {
    "operations": ["Write", "Describe", "Create"],
    "resource": {
        "name": "baz",
        "patternType": "literal",
        "type": "topic"
    }
    }
    assert expected_acl == manifests["KafkaUser"]["spec"]["authorization"]["acls"][0]
