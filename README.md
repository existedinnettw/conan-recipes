# conan-recipes

The goal of this repo is provide some **non-official** recipes for libraries that has no plan to officially support conan.

## CI/CD

* `ci.yml` validates only recipe/version targets changed by a pull request.
* `cd.yml` runs on `main`, builds only changed recipe/version targets, and uploads only missing packages to the configured private Conan remote.
* Populate secrets from `.env.ci.example` or `.env.ci` with `gh secret set -f .env.ci`.

## ref

* bibliography: [conan-center-index](https://github.com/conan-io/conan-center-index/tree/master)
* [audacity/conan-recipes](https://github.com/audacity/conan-recipes)
* [bkinnightskytw/ethercat](https://gitlab.com/bkinnightskytw/ethercat/-/tree/backport/1.5.3-conan?ref_type=heads) (recipe: `igh-ethercat`)
