pkgname=crossref-tool
pkgver=0.1.0
pkgrel=1
pkgdesc="Crossref REST API CLI for DOI and metadata workflows"
arch=('any')
url="https://api.crossref.org/"
license=('custom')
depends=('python')
makedepends=('python-build' 'python-installer' 'python-wheel' 'python-setuptools')
source=()
sha256sums=()

build() {
  cd "$startdir"
  rm -rf build dist *.egg-info src/*.egg-info src/crossref_tool.egg-info
  python -m build --wheel --no-isolation
}

package() {
  cd "$startdir"
  python -m installer --destdir="$pkgdir" dist/*.whl
  install -Dm644 README.md "$pkgdir/usr/share/doc/$pkgname/README.md"
  install -Dm644 PROJECT_OUTLINE.md "$pkgdir/usr/share/doc/$pkgname/PROJECT_OUTLINE.md"
}
