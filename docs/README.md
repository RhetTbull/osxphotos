# Building the documentation

I'm still trying to learn sphinx and come up with a workflow for building docs.  Right now it's pretty kludgy.

- `pip install sphinx`
- `pip install sphinx-rtd-theme`
- `pip install m2r2`
- Download and install [MacTeX](https://tug.org/mactex/)
- Add `/Library/TeX/texbin` to your `$PATH`
- `cd docs`
- `make html`
- `make latexpdf`
- `cp _build/latex/osxphotos.pdf .`
