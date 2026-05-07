from browser_factory import create_driver, random_delay

d = create_driver()
d.get("https://www.google.es")
print("Browser OK:", d.title)
d.quit()
