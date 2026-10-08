PATCH

**`slipwai search` and `slipwai install` work without being told where the chandlery is.** The default index
was derived from the keel's own forge URL, which produced a path that has never served an index — so every
command that reads the chandlery failed with *it is not a chandlery index* unless `SLIPWAI_INDEX` was set.

```console
$ slipwai search
  go            language  1.0.0  available  backends: go
  typescript    language  1.0.0  available  backends: typescript
  …
```

Where the keel lives and where the chandlery is published are two different things, and deriving one from
the other is what broke it. The default is written out now, and a test refuses one derived from the forge
again.

This is also what stopped the package repositories' CI fetching the family a framework is proved beside.

**Catch-up:** unset `SLIPWAI_INDEX` if you set it to work around this. A private channel still goes in
`SLIPWAI_CHANDLERY`, which is unchanged.
