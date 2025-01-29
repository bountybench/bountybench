import pytest
from calculator import Calculator

class TestCalculator:
    @pytest.fixture
    def calculator(self):
        """Fixture that creates a Calculator instance for each test"""
        return Calculator()
    
    def test_add(self, calculator):
        """Test basic addition"""
        assert calculator.add(1, 2) == 3
        assert calculator.add(-1, 1) == 0
        assert calculator.add(0, 0) == 0
    
    def test_subtract(self, calculator):
        """Test basic subtraction"""
        assert calculator.subtract(3, 2) == 1
        assert calculator.subtract(2, 3) == -1
        assert calculator.subtract(0, 0) == 0
    
    def test_multiply(self, calculator):
        """Test basic multiplication"""
        assert calculator.multiply(2, 3) == 6
        assert calculator.multiply(-2, 3) == -6
        assert calculator.multiply(0, 5) == 0
    
    def test_divide(self, calculator):
        """Test basic division"""
        assert calculator.divide(6, 2) == 3
        assert calculator.divide(5, 2) == 2.5
        assert calculator.divide(0, 5) == 0
    
    def test_divide_by_zero(self, calculator):
        """Test division by zero raises ValueError"""
        with pytest.raises(ValueError):
            calculator.divide(1, 0)