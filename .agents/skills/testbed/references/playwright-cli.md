# playwright-cli for test-bed debugging

[playwright-cli](https://github.com/microsoft/playwright-cli) drives a browser from the shell, so an agent can open the live portal of a running test bed and read the page, its requests and its bundle.
It is not a dependency of the repo: install it into a scratch directory outside the clone when you need it.

```bash
mkdir -p /tmp/pwcli && cd /tmp/pwcli
npm install @playwright/cli@0.1.22
mkdir -p .playwright && echo '{"browser":{"browserName":"chromium"}}' > .playwright/cli.config.json
export NO_UPDATE_NOTIFIER=1   # it checks npm for updates otherwise; it sends no telemetry
./node_modules/.bin/playwright-cli install-browser chromium
./node_modules/.bin/playwright-cli open http://localhost
```

Its own usage guide is `node_modules/@playwright/cli/skills/playwright-cli/SKILL.md`; `close-all` ends every browser session it started.

Use it for a fault the portal shows on its own, such as a wrong button or a failing request, with the cluster in the state the suite leaves before the failing feature.
It cannot attach to the suite's pytest browser, so a failure that depends on what an earlier test left in the shared session needs the trace (`TB_TRACE=all`).
