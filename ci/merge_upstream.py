#!/usr/bin/env python
"""Merge an upstream OpenUSD revision, retaining CI files and updating the submodule.

Leaves the merge staged for review and commit. Resolve any CI conflicts manually.
"""

import argparse
from pathlib import Path
import subprocess
import sys
import traceback


RETAINED_FILES = {
    ".gitattributes", ".gitignore", ".gitmodules", "LICENSE.txt", "NOTICE.txt",
    "OpenUSD",
}
RETAINED_DIRS = {".github", "build_scripts", "ci"}


def git(*args, cwd=None, check=True, input=None):
    return subprocess.run(
        ["git", *args], cwd=cwd, check=check, input=input,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )


def merge_upstream(ref):
    root = Path(git("rev-parse", "--show-toplevel").stdout.decode().strip())
    source = root / "OpenUSD"
    if git("status", "--porcelain", "--untracked-files=all", cwd=root).stdout:
        raise RuntimeError("Commit or stash all changes before merging upstream.")
    if not (source / "CMakeLists.txt").is_file():
        raise RuntimeError("Initialize the OpenUSD submodule before merging.")
    revision = git("rev-parse", "--verify", ref + "^{commit}", cwd=root).stdout.decode().strip()
    git("cat-file", "-e", revision + ":CMakeLists.txt", cwd=root)
    if git("merge-base", "--is-ancestor", revision, "HEAD", cwd=root, check=False).returncode == 0:
        print("Upstream revision is already merged.")
        return

    # Import the exact fetched upstream commit from the containing repository.
    git("fetch", "--no-tags", str(root), revision, cwd=source)
    result = git("merge", "--no-commit", "--no-ff", "--no-autostash", revision,
                 cwd=root, check=False)
    merge_head = git("rev-parse", "--verify", "MERGE_HEAD", cwd=root, check=False)
    if result.returncode not in (0, 1) or merge_head.returncode:
        raise RuntimeError(result.stderr.decode() or result.stdout.decode())

    paths = set(git("ls-files", "-z", cwd=root).stdout.split(b"\0")) - {b""}
    removed = sorted(
        path for path in paths
        if path.decode() not in RETAINED_FILES
        and path.decode().split("/", 1)[0] not in RETAINED_DIRS
    )
    if removed:
        git("--literal-pathspecs", "rm", "-r", "-f", "--ignore-unmatch",
            "--pathspec-from-file=-", "--pathspec-file-nul", cwd=root,
            input=b"\0".join(removed) + b"\0")
    git("checkout", "--detach", revision, cwd=source)
    git("add", "OpenUSD", cwd=root)
    conflicts = git("diff", "--name-only", "--diff-filter=U", cwd=root).stdout.decode()
    if conflicts:
        raise RuntimeError("Resolve and stage retained CI conflicts, then review and "
                           "commit the merge:\n" + conflicts)
    print("Merge staged with OpenUSD pinned to " + revision)
    print("Review git diff --cached, validate CI, then git commit.")


def get_parser():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("ref", help="Fetched upstream ref, for example pixar/dev")
    return parser


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    args = get_parser().parse_args(argv)
    try:
        merge_upstream(args.ref)
    except Exception:
        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
