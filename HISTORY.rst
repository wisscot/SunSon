.. :changelog:

Release History
---------------

dev
+++

**Improvements**

- Warn user about possible slowdown when using cryptography version < 1.3.4
- Check for invalid host in proxy URL, before forwarding request to adapter.
- Fragments are now properly maintained across redirects. (RFC7231 7.1.2)

**Bugfixes**

- Parsing empty ``Link`` headers with ``parse_header_links()`` no longer return one bogus entry
- Fixed issue where loading the default certificate bundle from a zip archive
  would raise an ``IOError``
- Fixed issue with unexpected ``ImportError`` on windows system which do not support ``winreg`` module
- DNS resolution in proxy bypass no longer includes the username and password in
  the request. This also fixes the issue of DNS queries failing on macOS.


1.0 (2018-02-22)
++++++++++++++++++

* Birth!


