PATCH

**An answer taken away takes its state-move blocks with it.** The internal/external identity rename of
2026-10-08 added `moved {}` blocks to five stack files so that the first apply after the rename moves state
instead of destroying it. They were written after each file's `backing-service:…:end` marker, which put them
outside the answer they belong to — so `./init --auth none` emptied the region and left behind state moves
for resources the pruned stack no longer defines.

`tofu validate` accepts them, which is why nothing had noticed: a `moved` block whose source is gone is a
no-op. What it is not is honest — a file that should be empty was carrying thirteen blocks about resources
the project had just said it did not want. They are inside their regions now, on both clouds, for the
internal, external and Auth0 answers.
