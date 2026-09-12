cp /app/script/* /app/workspace -r
repo_url=$(jq -r '.repo_url' /app/vars.json)
echo repo_url=$repo_url
git clone $repo_url repo
cargo run