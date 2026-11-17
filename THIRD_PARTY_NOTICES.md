# Third-party notices

## AeroTizen

iTV builds on [AeroTizen](https://github.com/helalaou/AeroTizen), pinned to commit
`8ec95131a9339df90d4dd0c2435e794ae192c19d` (see [upstream.lock.json](upstream.lock.json)).
The build clones that commit and applies the patches in [patches/](patches/). The patches
modify AeroTizen source, so they are distributed under AeroTizen's license:

```text
MIT License

Copyright (c) 2026 Hamza El Alaoui

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## App logos and trademarks

Patch `0002-itv-home-ui.patch` includes the logos of Netflix, Spotify, YouTube, Disney+,
HBO Max, Prime Video and PlayStation, taken from Wikimedia Commons. They are
trademarks of their respective owners. They are used only to identify the apps
installed on the TV; this project is not affiliated with or endorsed by any of
those companies, or by Samsung.

Samsung, Tizen and Smart Hub are trademarks of Samsung Electronics. Apple TV and
tvOS are trademarks of Apple Inc. They are mentioned only as a design reference.
