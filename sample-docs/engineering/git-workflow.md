# Git workflow

Nobody pushes directly to main. Create a branch per change named type/short-description, for example fix/login-timeout. Keep pull requests under 400 lines where possible.

Every pull request needs one approving review and passing CI before merging. Use squash merge, and write the commit message in the imperative mood, like "add retry to payment client".
