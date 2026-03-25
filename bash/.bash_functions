mp4togif() {
  if [ $# -ne 2 ]; then
    echo "Usage: mp4togif input.mp4 output.gif" >&2
    return 1
  fi
  ffmpeg -i "$1" -vf "fps=10,scale=480:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" -loop 0 "$2"
}