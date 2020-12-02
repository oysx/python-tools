class A:
    mm = 10


a = A()
print(a.mm==A.mm)
b = A()
print(b.mm==A.mm)
a.mm = 20
print(a.mm==A.mm)
print(b.mm==A.mm)

print(type(10))

'''Result:
True
True
False
True
<type 'int'>
'''