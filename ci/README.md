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
