# Third-Party Notices

NVIDIA TAO DAFT incorporates the following open-source software. Each
component is distributed under its own license; this notice is provided in
accordance with the redistribution requirements of those licenses.

This file complements — but does not replace — the [LICENSE](LICENSE) under
which NVIDIA TAO DAFT itself is released (Apache License, Version 2.0).

---

## Runtime dependencies

The published `nvidia-tao-daft` wheel declares the following direct runtime
dependencies in `pyproject.toml`. Each is installed alongside this package
when users `pip install nvidia-tao-daft`.

### jsonschema

- **Project:** https://github.com/python-jsonschema/jsonschema
- **License:** MIT License
- **Copyright:** Copyright (c) 2013 Julian Berman

```
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
```

---

### pydantic

- **Project:** https://github.com/pydantic/pydantic
- **License:** MIT License
- **Copyright:** Copyright (c) 2017 to present Pydantic Services Inc. and individual contributors

```
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
```

---

## Notes

- This file lists only **direct** runtime dependencies declared in
  `pyproject.toml`. Transitive dependencies installed by `pip` carry their
  own license metadata in their respective distributions and are not
  re-listed here.
- Development tooling declared under `[dependency-groups]` in `pyproject.toml`
  is not shipped with the published wheel and is therefore not enumerated.
- If you add, remove, or upgrade a runtime dependency, update this file in
  the same change.
