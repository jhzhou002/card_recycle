import random


def generate_math_captcha():
    """生成数学运算验证码"""
    # 随机选择运算类型
    operation_type = random.choice(['add', 'subtract', 'multiply'])
    
    if operation_type == 'add':
        # 加法：两个1-20的数相加
        num1 = random.randint(1, 20)
        num2 = random.randint(1, 20)
        question = f"{num1} + {num2} = ?"
        answer = str(num1 + num2)
        
    elif operation_type == 'subtract':
        # 减法：确保结果为正数
        num1 = random.randint(10, 30)
        num2 = random.randint(1, num1 - 1)  # 确保结果为正
        question = f"{num1} - {num2} = ?"
        answer = str(num1 - num2)
        
    else:  # multiply
        # 乘法：小数相乘
        num1 = random.randint(2, 9)
        num2 = random.randint(2, 9)
        question = f"{num1} × {num2} = ?"
        answer = str(num1 * num2)
    
    return question, answer


def generate_captcha():
    """生成验证码（兼容原接口）"""
    question, answer = generate_math_captcha()
    return answer, question  # 返回答案和问题，保持原有接口兼容性


# 保持向后兼容的函数
def generate_captcha_text(length=4):
    """兼容性函数 - 现在返回数学运算答案"""
    _, answer = generate_math_captcha()
    return answer


def generate_captcha_image(text, width=200, height=80):
    """兼容性函数 - 现在返回数学运算问题"""
    question, _ = generate_math_captcha()
    return question