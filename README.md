## Simple session time tracking


### Requirements:
- python 3.x


### Install:
`./main.py init`
It doesn't have a `setup.py`, symlink will be easiest option.


### Usage:
- Start `trac start <project> <task>`
- Stop `trac close <project> <task>`
- Report `trac report`
- Total spent time on _closed_ or _open_ project or a specific project, task `trac time {closed,open} [project] [task]`
- _closed_ or _open_ session count (only 1 session can be opened at same time) `trac count {closed,open}`
- Toggle task start, stop `trac toggle <project> <task>`
- Delete whole project or a specific task inside a project `trac delete <project> [task]`
- Delete everything `trac truncate`

