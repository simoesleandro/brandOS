# fix_requirements.py
data = open("requirements.txt", "rb").read()
text = data.decode("utf-8", errors="ignore").replace("\x00", "")
lines = [l.strip() for l in text.splitlines() if l.strip()]

with open("requirements.txt", "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(lines) + "\n")

print("Corrigido. Conteúdo final:")
print(open("requirements.txt", encoding="utf-8").read())