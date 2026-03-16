pkgname=crossref-cli-git
_pkgname=crossref-cli
pkgver=0.1.0.r1.g5215d6b
pkgrel=1
pkgdesc="Crossref REST API CLI for DOI and metadata workflows"
arch=('any')
url="https://github.com/Schmoho/crossref-cli"
license=('MIT')
depends=('python')
makedepends=('git' 'python-build' 'python-installer' 'python-wheel' 'python-setuptools')
provides=('crossref-cli' 'crossref-tool')
conflicts=('crossref-cli' 'crossref-tool')
source=("git+https://github.com/Schmoho/crossref-cli.git")
source+=("LICENSE")
sha256sums=('SKIP'
            '532ab52473158a8880890c1f061cd633a6388028d968fb9aa85ba1f8a776d529')

pkgver() {
  cd "$_pkgname"
  printf '0.1.0.r%s.g%s' "$(git rev-list --count HEAD)" "$(git rev-parse --short HEAD)"
}

build() {
  cd "$_pkgname"
  rm -rf build dist *.egg-info src/*.egg-info src/crossref_tool.egg-info
  python -m build --wheel --no-isolation
}

package() {
  cd "$_pkgname"
  python -m installer --destdir="$pkgdir" dist/*.whl
  install -Dm644 README.md "$pkgdir/usr/share/doc/$pkgname/README.md"
  install -Dm644 "$srcdir/LICENSE" "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}
