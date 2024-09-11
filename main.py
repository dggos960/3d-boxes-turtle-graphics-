import turtle
import random

# Set up the screen
screen = turtle.Screen()
screen.setup(width=680, height=800)  
screen.bgcolor("black")

# Create a turtle named "illusion_turtle"
illusion_turtle = turtle.Turtle()
illusion_turtle.speed(0)  # Fastest drawing speed
illusion_turtle.width(2)

# Function to generate a random color
def random_color():
    return (random.random(), random.random(), random.random())

# Function to draw a pulsating spiral
def draw_pulsating_spiral():
    illusion_turtle.penup()
    #illusion_turtle.goto(-300, -300)  # Move the turtle to the bottom-left corner
    illusion_turtle.pendown()

    for i in range(140):
        illusion_turtle.pencolor(random_color())  # Set a random color
        illusion_turtle.forward(i * 6)  # Move forward with increasing distance
        #illusion_turtle.right(90)  # Turn right
        illusion_turtle.forward(i * 6)  # Move forward again
        illusion_turtle.right(90)  # Turn right
        illusion_turtle.forward(i * 6)  # Move forward again
        illusion_turtle.right(90)  # Turn right
        illusion_turtle.forward(i * 6)  # Move forward again
        illusion_turtle.right(90)  # Turn right
        illusion_turtle.backward(i * 6)  # Move backward
        illusion_turtle.left(90)  # Turn left
        illusion_turtle.backward(i * 6)  # Move backward again
        illusion_turtle.left(90)  # Turn left
        illusion_turtle.backward(i * 6)  # Move backward again
        illusion_turtle.left(90)  # Turn left
        illusion_turtle.backward(i * 6)  # Move backward again
        illusion_turtle.left(90)  # Turn left

# Draw the pulsating spiral
draw_pulsating_spiral()

# Hide the turtle and finish
illusion_turtle.hideturtle()
turtle.done()
