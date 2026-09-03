"""The trades worth walking into, grouped the way you would plan a day.

Chosen for two things: the business is local enough that the owner decides, and
a website plausibly wins them work. A dentist and a plumber both qualify; a bank
branch does not, because nobody at that address can buy anything.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Category:
    key: str
    label: str
    query: str          # what to ask Google
    blurb: str


CATEGORIES: tuple[Category, ...] = (
    Category("restaurants", "Restaurants & cafés", "restaurant",
             "Menus, hours and photos go stale fastest here."),
    Category("hvac", "HVAC & plumbing", "HVAC contractor OR plumber",
             "Emergency trades — customers search on a phone, in a hurry."),
    Category("home", "Home services", "roofing contractor OR landscaping OR electrician",
             "Quote-driven work where a gallery does the selling."),
    Category("auto", "Auto services", "auto repair shop OR car detailing",
             "Trust and reviews matter more than price."),
    Category("beauty", "Salons & spas", "hair salon OR nail salon OR day spa",
             "Booking links and a gallery are most of the site."),
    Category("fitness", "Gyms & studios", "gym OR yoga studio OR martial arts school",
             "Schedules and class descriptions change constantly."),
    Category("pro", "Local professionals", "dentist OR chiropractor OR law firm",
             "Higher budgets; a dated site costs them credibility."),
    Category("shops", "Independent shops", "florist OR bakery OR bike shop",
             "Small owners, quick decisions, visible storefronts."),
)

BY_KEY = {c.key: c for c in CATEGORIES}
