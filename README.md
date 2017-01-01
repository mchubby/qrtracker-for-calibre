# About this Plugin

**QRCode Tracker Filidel** is a free and open source plugin for e-book library management application [Calibre](https://calibre-ebook.com/). It runs in “Edit Book” mode.

Its main purpose is to append a QR code at the end of each chapter in a book. When scanned, this code is converted into a message to help you keep track of your reading progress.

Its use case is for e-readers that are for a reason or another disconnected from internet.

# Installing

 * **Calibre 2.61 or later** is required
 * Download a zipped copy of this repository, using a [tagged release](https://github.com/mchubby/qrtracker-for-calibre/releases/latest). Notice: at this point, Calibre requires files packed inside zip to sit at **top-level of archive** and not in a subdirectory. Download the zip marked as **RELEASE**.
 * Install this ZIP using the Calibre "preferences > plugins" dialog. [Click here for a tutorial with images](http://www.ismoothblog.com/2012/07/how-to-install-plugin-to-calibre.html) in case you cannot find it.

# Using
 * Open a book in the calibre editor
 * Click **Menu Plugins -> “Filidel: Add QR trackers”**
 * Review changes to your book, then save.

# License and contributing
 * [Contributors list](docs/CONTRiBUTORS.txt)
 * You are free to copy and redistribute under the terms of the [GNU General Public License, version 3 or later](LICENSE). Translated versions are available on the [GNU website](https://www.gnu.org/licenses/translations.html).
 * A modified copy of [qrcode 5.3](https://github.com/lincolnloop/python-qrcode/releases/tag/v5.3) is bundled. As per its [license](licenses/QRCODE_LICENSE), the combined work is licensed under the GPLv3. To obtain the original, unmodified MIT-licensed library, visit [the original repository](https://github.com/lincolnloop/python-qrcode)
 * For more information on contributing, refer to the [CONTRIBUTING.md](.github/CONTRIBUTING.md) document

