MINOR

**A project that elected no extension is no longer handed one extension's tool name.**
`scripts/agents/registry.json` is the keel's catalogue of coding agents and it travels into every generated
project. Claude Code's headless row carried `--allowedTools 'Bash,Skill,Agent,WebFetch,WebSearch,mcp__codegraph__*'`,
so every project ran its sessions under an allow-list naming the code index whether it had elected the
index or not — and a reader finding it there had every reason to think the keel brought it.

An `extension.json` now declares `tools` beside `hooks` and `guards`: the names a headless session must be
allowed to call to reach that extension, as a list of strings in the harness's own spelling. The generator
writes them to `scripts/extensions/available-tools.json` the way it already writes the other two,
`hooks.py --elect` records the elected ones in `.slipwai/hooks.json`, and a harness row says where they go
with a `{tools}` placeholder **inside** the allow-list it already has — a second `--allowedTools` flag is
not a merge on every harness that has one. A row with no placeholder is left exactly as recorded rather
than handed a flag nobody has checked it accepts.

Nothing is validated against a harness. A tool pattern is the harness's spelling, and a keel that checked
them would be a keel that has to be released before an extension can use a tool it invented. What is held
is the shape, and `tests/test_extension_reach.py` holds the registry to carrying no extension's name in any
value a session runs under — `permissions`, `command`, `env` and the rest, as against a `source` or a
`projectMcpReason`, which are dated evidence and stay as recorded.

**The keel says *the code index* for the thing.** Twenty-nine notes in the registry and the architecture
view's own prose named the product where they meant the capability. The product is still named where the
keel is naming a file format or quoting what a file says wrote it: `slipwai survey` opens
`.codegraph/codegraph.db` if it is there, the way it reads `.git`, and `./init --extension codegraph` is
still the command a refusal gives you.

**Catch-up:** a project that elected codegraph before this generates the identical session command, because
the election now supplies the name the registry used to. One that elected nothing loses a tool name from
its allow-list that nothing in it could reach.
