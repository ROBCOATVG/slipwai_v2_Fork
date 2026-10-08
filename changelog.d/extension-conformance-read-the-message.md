PATCH

**Three checks an extension is held to were wrong about the thing they were reading.** The three published
extensions had never run conformance — no CI at all — so nothing had said so.

- **`recovers` read line by line.** Every real message is written the other way: the trouble, then
  `Install it:`, then the command, indented. So the first line of every one of them failed and the command
  two lines below was never seen. It reads a message now — a problem line and the lines under it — and a
  problem with nothing after it still fails.
- **`./init` could never be recognised as a remedy.** The pattern had a word boundary before it, and the
  character before `.` in `  ./init --extension uipro` is a space, so `\b\./init` matched nothing. It is the
  one command every extension names.
- **`projects` only excused a stop for a missing tool**, recognised by words like *not found*. The scratch
  project it runs in is deliberately bare, so an extension that acts on a browser app correctly does nothing
  there and says `this project has no browser app for it to design` — no such words, failed for doing the
  right thing. What makes a stop legitimate is that it names the way on, which is what obligation 6 already
  asks of it.

**Catch-up:** nothing. Three packages that were conforming all along now say so.
