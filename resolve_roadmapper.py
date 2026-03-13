with open(".jules/roadmapper.md", "r") as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if line.startswith("<<<<<<<"):
        skip = True
    elif line.startswith("======="):
        skip = False
    elif line.startswith(">>>>>>>"):
        continue
    elif not skip:
        new_lines.append(line)

with open(".jules/roadmapper.md", "w") as f:
    f.writelines(new_lines)
