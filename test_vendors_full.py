from vendor_finder import VendorFinder

# ---------------- INITIALIZE FINDER ----------------
finder = VendorFinder()

# ---------------- SERVICES TO TEST ----------------
services_to_test = [
    ("plumber", "Abuja"),
    ("electrician", "Abuja"),
    ("cake", "Abuja"),
    ("photographer", "Abuja")
]

# ---------------- HELPER FUNCTION ----------------
def print_vendors(results, service, location):
    vendors = results.get("vendors", [])
    print(f"\n🔹 {service.title()} in {location} — {len(vendors)} vendors found")
    for i, v in enumerate(vendors, 1):
        identity = v.get("identity", {})
        contacts = v.get("contacts", {})
        social = v.get("social", {})
        location_info = v.get("location", {})

        print(f"Vendor #{i}: {identity.get('name', 'N/A')}")
        print(f"   Confidence Score: {v.get('confidence_score')}")
        print(f"   URL: {identity.get('url')}")
        print(f"   Instagram: {', '.join(social.get('instagram', [])) or 'Not found'}")
        print(f"   WhatsApp: {', '.join(contacts.get('whatsapp', [])) or 'Not found'}")

        # Optional: Google Maps info
        gm = location_info.get("google_maps")
        if gm:
            print(f"   Address: {gm.get('address')}")
            if gm.get("rating"):
                print(f"   Rating: {gm.get('rating')}")

        print("-" * 40)

# ---------------- RUN TESTS ----------------
for service, location in services_to_test:
    print(f"\n🔎 Searching for '{service}' in '{location}' ...")
    results = finder.find_vendors(service, location)
    print_vendors(results, service, location)
