## v0.1.0

This release includes some non-backwards compatible changes to the schema. Old
json files will need to be updated. The main change is that with the addition of
adding 2D slices, the region selection from v0.0.1 has been nested within a
`SelectionObject` level.

### New Features

* can now load 2D slices
* widget reader redesign: add multiple selections!
* yt dataset cacheing to speed up subsequent loads
* improved logging
* test infrastructure updates
* improved development maintenance scripts
