#### Contributing to NVIDIA TAO DAFT

* We require that all contributors "sign-off" on their commits. This certifies that the contribution is your original work, or you have rights to submit it under the same license, or a compatible license.

  * Any contribution which contains commits that are not Signed-Off will not be accepted.

* To sign off on a commit you simply use the `--signoff` (or `-s`) option when committing your changes:
  ```bash
  $ git commit -s -m "Add cool feature."
  ```
  This will append the following to your commit message:
  ```
  Signed-off-by: Your Name <your@email.com>
  ```

* Full text of the DCO (https://developercertificate.org/):

  ```
    Developer Certificate of Origin
    Version 1.1

    Copyright (C) 2004, 2006 The Linux Foundation and its contributors.

    Everyone is permitted to copy and distribute verbatim copies of this
    license document, but changing it is not allowed.


    Developer's Certificate of Origin 1.1

    By making a contribution to this project, I certify that:

    (a) The contribution was created in whole or in part by me and I
        have the right to submit it under the open source license
        indicated in the file; or

    (b) The contribution is based upon previous work that, to the best
        of my knowledge, is covered under an appropriate open source
        license and I have the right under that license to submit that
        work with modifications, whether created in whole or in part
        by me, under the same open source license (unless I am
        permitted to submit under a different license), as indicated
        in the file; or

    (c) The contribution was provided directly to me by some other
        person who certified (a), (b) or (c) and I have not modified
        it.

    (d) I understand and agree that this project and the contribution
        are public and that a record of the contribution (including all
        personal information I submit with it, including my sign-off) is
        maintained indefinitely and may be redistributed consistent with
        this project or the open source license(s) involved.
  ```

## Development setup

Install the git hooks once per clone:

```bash
pip install pre-commit pylint pydocstyle flake8 && pre-commit install
```

That installs both the `pre-commit` and `commit-msg` hooks. The first commit
afterwards takes a few minutes while the hook environments are built; later
commits are fast.

If you previously ran `git config core.hooksPath .github/hooks`, unset it first.
It overrides the hooks installed above, and they will silently never run:

```bash
git config --unset core.hooksPath
```

## What runs on every commit

| Check | Blocks on |
|-------|-----------|
| TruffleHog | a credential in the staged changes |
| dependency guard | any change to a dependency manifest, lockfile or Dockerfile |
| license header | a `.py` or `.sh` file without an SPDX header |
| pylint, pydocstyle, flake8 | lint and docstring violations |
| DCO sign-off | a commit message without a `Signed-off-by` trailer |

Only the files you changed are checked, never the whole repository. To run them
by hand:

```bash
# only what your branch changed vs main
pre-commit run --from-ref origin/main --to-ref HEAD

# or everything
pre-commit run --all-files
```

## Dependency changes

Changes to dependency manifests, lockfiles and Dockerfiles are blocked at commit
time, in every language:

```
Dependency change blocked. This commit modifies:
  requirements.txt

Please reach out to TAO Infra team for dependency change
```

This is deliberate. Raise the change with the TAO Infra team rather than working
around the hook.
