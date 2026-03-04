# Quick quide on Github.

Github is a platform build on Git and owned by Microsoft, that is the worst part. Github is a place where you can share and manage projects. I'll explain 3 things that are in my opinon the most important part of Git & Github. If there are any questions, just hit me up.

## Git
Git is the base on where Github & Gitlab are build on. Its made by the creator of Linux (the best operation system out there). Git is a small program that can be used to share files to a server. In our case the server is Github, using Git you can send (push) and recive (pull) files and file changes.

Git is made for CLI (command line interface). Its the scary lines on your computer. Its a way to talk about your system and get it to do things, so really powerfull, try it out once.

Ill give you a small guide of commands you can use. Just because I think its good to know it, but nowadays Git is build into editors. So most editors got some buttons to commit, push and pull your files.

*Most common used commands:*
- `~ git status` : This show the files that differ from what is known on the server. This gives you the opportunity to make sure to see what you have worked on and what you want to store on the server.

- `~ git add ( '.' or 'filename)` : This command lests you add a file to a commit. (commit is an update you send to the server). `~ git add . ` lets you commit all files you changes. After using the add command you can check what you've added to the commit.

- `~ git commit -m "(description)"` : This command lets you create the commit you send files to and gives you the possibilty to add an text. (for example: I will name this 'Github guide'. Its so you know what you've pushed to the server)

- `~ git push` : this is the command to push your commit to the server. This is hard to redo so check it with `git status` before doing it.

- `~ git pull` : This command lets you update your local folder from the server. So all new work added to the server will be on your system.