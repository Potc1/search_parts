arr = ['q', 'y', 'u', 'p', 'f', 'h', 'j', 'k', 'z', 'x', 'v']
#dict = {"foqrl": 1, ""}
counter = 0
first_part = "lo"
word = "lo"
for i3 in arr:
    word += i3
    word += 'r'
    for i5 in arr:
        counter += 1
        print(word + i5)
    word = "lo"

print(f"Total words = {counter}")