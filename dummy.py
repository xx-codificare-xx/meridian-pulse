def func(n):
    if n <=1:
        return 1
    return n * func(n-1)

n = 5
result = func(n)
print(result)