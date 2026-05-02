# Navigation
alias ..='cd ..'
alias ...='cd ../..'
alias -- -='cd -'          # go back to previous directory

# Listing
alias ll='ls -alF'
alias lt='ls -ltr'         # list by time, newest last
alias la='ls -A'

# Safety net (ask before overwriting)
alias rm='rm -i'
alias cp='cp -i'
alias mv='mv -i'

# Git shortcuts
alias gs='git status'
alias ga='git add .'
alias gc='git commit -m'
alias gp='git push'
alias gl='git log --oneline --graph --decorate'
alias gco='git checkout'

# Docker shortcuts
alias dps='docker ps'
alias dc='docker-compose'
alias dcu='docker-compose up -d'
alias dcd='docker-compose down'

# Dev shortcuts
alias ni='npm install'
alias nrd='npm run dev'
alias nrb='npm run build'

# Reload shell config after editing
alias reload='source ~/.bashrc'

# lerobot
alias conda-lerobot='conda activate lerobot'
alias lerobot-env='conda-lerobot && cd ~/lerobot_ws/so101ai'
alias jupyter-lerobot='lerobot-env && jupyter-lab'

