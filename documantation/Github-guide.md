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

## Github
Github previously mentioned owned my Microsoft is a website that lets you see and store project files. You can follow other developers, see public repos that are open source and track your own. For this project we will be focused on our own project. 

An important step for Git and Github to work together is making a SSH key, I wont go into dept what that is. You can look it up or ask me if you want to know it. Making an SSH key isn't difficult if you know what you need to do. Github has some great documantation on it (https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent). This will guide you trough the steps. If you need any help let me know. 

Version control is a important topic, especilly when you are working with a team on a big project. To not mess up someones or your own work you have to be carefull. The best way to not mess things up is working in branches. Think of it like a copy of a painting so you can do your own thing without having to worry about the original painting.

You can push your code/work onto your branch and then make a 'merge request' to add it to the main branch (the original painting). Someone else then checks your work and makes sure it wont break anything and your code alligns with the code conventions (some rules about how your code should look like).

After the green light of a college you can push your code onto the main branch.

## Github planning

Github is used for big projects, think about your banking app and the social media platform X. Some big projects with a lot of developers and testers on it. To stay on top of the development and the work that need or has been done Github works with issues/task.

For example a new feature gets an issue where you can read what needs to be done, when will it be done and who is going to work on it. This makes a project run smooth and the boss knows who is slacking. For this project we can work with issues so we dont forget anything that needs to be done.

Let me know if there are any... opsss
