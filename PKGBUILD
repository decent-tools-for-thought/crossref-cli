pkgname=crossref-cli
_pkgname=crossref-cli
pkgver=0.1.0
pkgrel=1
pkgdesc="Crossref REST API CLI for DOI and metadata workflows"
arch=('any')
url="https://github.com/decent-tools-for-thought/crossref-cli"
license=('MIT')
depends=('python')
makedepends=('python-build' 'python-installer' 'python-wheel' 'python-setuptools')
provides=('crossref-tool')
conflicts=('crossref-cli-git' 'crossref-tool')
source=("$_pkgname-$pkgver.tar.gz::https://github.com/decent-tools-for-thought/crossref-cli/archive/refs/tags/v$pkgver.tar.gz"
        "LICENSE")
sha256sums=('0a6234d613941c6134742f6ccca7baafc44f727918d0123a178cac0b7d11792f'
            '532ab52473158a8880890c1f061cd633a6388028d968fb9aa85ba1f8a776d529')

build() {
  cd "$_pkgname-$pkgver"
  rm -rf build dist *.egg-info src/*.egg-info src/crossref_tool.egg-info
  python -m build --wheel --no-isolation
}

package() {
  cd "$_pkgname-$pkgver"
  python -m installer --destdir="$pkgdir" dist/*.whl
  install -Dm644 README.md "$pkgdir/usr/share/doc/$pkgname/README.md"
  install -Dm644 "$srcdir/LICENSE" "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}
