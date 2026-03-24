lsof -i :3000 | awk 'NR > 1 {print $2}' | xargs kill
lsof -i :5050 | awk 'NR > 1 {print $2}' | xargs kill
