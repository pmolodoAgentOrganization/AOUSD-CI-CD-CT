# AOUSD CI/CD/CT trial

This branch retains the OpenUSD Git history and CI code, with product source
provided by the `OpenUSD/` submodule of PixarAnimationStudios/OpenUSD. The
submodule is pinned to a commit; workflow checkouts do not follow a moving branch.

## Layout

- `.github/`: GitHub workflows and contribution templates.
- `build_scripts/`: CI-owned build driver, platform helpers, and wheel packaging.
- `ci/`: maintenance tools and documentation for this split.
- `OpenUSD/`: upstream source, CMake build system, tests, and documentation.
- Root license, notice, and Git configuration files apply to the retained code.

CI executes the outer repository's workflows and build scripts. The submodule's
copies are intentionally retained but are not used as CI entry points.
`build_usd.py` defaults to the submodule as its source directory; `--usd-src`
selects another source checkout. Build and installation directories remain in
the outer workspace. GPU tests download that workspace from the Linux job.
Wheel packaging uses the license from the pinned source revision.

## Checkout and validation

```sh
git submodule update --init --recursive
python build_scripts/build_usd.py --help
python build_scripts/build_usd.py --dry_run --no-python --no-imaging --no-materialx /tmp/usd-ci-install
python -m unittest discover -s ci/tests -v
```

Pushes to `aousd-ci-cd-ct` run the native, WebAssembly, GPU, and packaging
workflows. Standard runners build USD; only the GPU test job uses the configured
T4 larger runner. The destination organization must grant this repository access
to that runner. Pull requests targeting the CI branch also validate workflow
changes; GPU tests remain push-only, following the upstream policy.

## Test an external OpenUSD repository

The OpenUSD Source repository invokes `BuildUSD` through `workflow_dispatch`.
The run is owned by this repository: it checks out this repository for workflow
and build code, then replaces `OpenUSD/` with the exact external commit from the
dispatch inputs. A source push receives the full push test policy, including GPU
tests; a source pull request receives the headless pull request policy and never
uses the self-hosted GPU runner.

The receiver fails closed unless the payload contains:

- source event `push` and either the `dev` or `build-ig` branch, or a tag matching
  `refs/tags/vNN.NN`; or
- source event `pull_request`, a positive pull request number, its matching
  `refs/pull/NUMBER/merge` ref, and a target branch of either `dev` or `build-ig`.

Both event types require the source repository configured by the
`OPENUSD_SOURCE_REPOSITORY` Actions variable and a full commit SHA.
`ci/resolve_source.py` validates this contract before any source checkout.

Dispatch inputs are serialized as strings, including `pull_request`, matching
the [GitHub CLI's workflow dispatch interface](https://cli.github.com/manual/gh_workflow_run).
The workflow declares `pull_request` as `type: number`; the Python receiver
reads the event JSON and validates its string value as a positive integer.

### Configure the GitHub App

1. Open the preconfigured registration page:

   ```sh
   ci/register_aousd_ci_cd_ct_github_app.sh CI_OWNER CI_REPO
   ```

   Review the form and create the App. It is owned by `CI_OWNER`, is private to
   that owner, has repository
   `Actions: Read and write` permission, and has webhooks and OAuth disabled.
   If the suggested App name is unavailable, choose another unique name.
2. Install it only on `CI_OWNER/CI_REPO` while testing.
3. In the OpenUSD Source repository, create Actions variable
   `AOUSD_CI_APP_ID` containing the App ID and secret
   `AOUSD_CI_APP_PRIVATE_KEY` containing its private key.
4. Copy `ci/dispatchers/openusd-source.yml` to
   `.github/workflows/aousd-ci-dispatch.yml` in the OpenUSD Source repository.

After creating and installing the App, appropriately authorized humans can
configure each repository independently:

```sh
ci/configure_openusd_source_repo.sh SOURCE_OWNER SOURCE_REPO CI_OWNER CI_REPO APP_ID /path/to/private-key.pem
ci/configure_aousd_ci_cd_ct_repo.sh CI_OWNER CI_REPO SOURCE_OWNER SOURCE_REPO
```

The first script targets only `SOURCE_OWNER/SOURCE_REPO`, the OpenUSD source
repository. It also records `CI_OWNER/CI_REPO` as the dispatch destination. The
second targets only `CI_OWNER/CI_REPO`, the AOUSD CI-CD-CT repository. Review
the scripts before running them. They intentionally use the human's `gh`
authentication and are not called by CI.

The OpenUSD Source repository currently uses `ci-testing` as its default branch.
GitHub requires a `pull_request_target` workflow to exist on the default branch,
while a `push` workflow must exist in the pushed revision. For the test
integration, either make `dev` the default branch before installing the
dispatcher, or keep the identical dispatcher file on both `ci-testing` and
`dev`.

The dispatcher creates a short-lived installation token scoped to only
`AOUSD-CI-CD-CT` and only `actions: write`, which is the permission GitHub's
workflow dispatch API requires. It sends events for pushes to `dev` or
`build-ig`, matching version tags, and non-draft pull requests targeting either
source branch.

The pull request trigger intentionally uses `pull_request_target` so App
credentials remain available for pull requests from forks. The dispatcher must
remain metadata-only: never add a source checkout, execute pull request code, or
pass additional secrets to it. Untrusted source is executed only by the receiving
BuildUSD workflow, which has read-only repository permissions and reserves its
self-hosted runner for trusted push events.

GitHub processes `workflow_dispatch` only when the receiving workflow exists on
the receiving repository's default branch. Before testing dispatch, either make
`aousd-ci-cd-ct` the testing repository's default branch or merge the CI split
into its current default branch, `dev`. See the GitHub documentation for
[workflow dispatch events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_dispatch),
[creating a workflow dispatch](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event),
and [creating GitHub App tokens](https://github.com/actions/create-github-app-token).

## Merge Pixar updates

Start with a clean checkout, including the submodule. Fetch upstream, then run:

```sh
git fetch pixar dev
python ci/merge_upstream.py pixar/dev
git diff --cached
```

The helper performs a normal merge without committing, removes incoming product
source from the outer tree, and pins the submodule to the merged upstream
revision. Source modify/delete conflicts are resolved by keeping the outer
deletions. Changes to retained CI files merge normally; conflicts in them stop
the helper and must be resolved and staged manually. New source files are also
removed from the outer tree. Review new upstream CI dependencies and extend the
helper's retained paths if CI code is introduced outside the existing directories.

After review and validation, commit the merge with `git commit`. This records
both parents so the next merge starts from the correct upstream merge base.
Do not use plain `git pull` on this branch: it does not apply the split policy.
To abandon a merge:

```sh
git merge --abort
git submodule update --init --recursive
```

Changes destined for Pixar should be ported as focused CI changes onto a normal
Pixar source branch. Do not merge this source-removal branch back into Pixar.

The history is preserved, so this trial reduces the checked-out outer tree,
not the size of its historical Git object database.

References: [Git submodules](https://git-scm.com/docs/git-submodule),
[Git merge](https://git-scm.com/docs/git-merge), and
[checkout submodule support](https://github.com/actions/checkout#checkout-submodules).
