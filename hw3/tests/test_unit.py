from main import generate_code

def test_generate_code_length():
    assert len(generate_code()) == 6
    assert len(generate_code(length=10)) == 10

def test_generate_code_uniqueness():
    codes = {generate_code() for _ in range(100)}
    assert len(codes) == 100 