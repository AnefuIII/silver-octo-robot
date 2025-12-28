from vendor_finder import VendorFinder

finder = VendorFinder()

plumber_results = finder.find_vendors("plumber", "Abuja")
electrician_results = finder.find_vendors("electrician", "Lagos")
cake_results = finder.find_vendors("cake", "Lagos")
photographer_results = finder.find_vendors("photographer", "Ibadan")

def print_vendors(results, service, location):
    vendors = results.get("vendors", [])
    print(f"\n🔹 {service.title()} in {location} — {len(vendors)} vendors found")
    for i, v in enumerate(vendors, 1):
        print(f"Vendor #{i}: {v.get('name')} — Confidence: {v.get('confidence_score')}")
        print(f"   URL: {v.get('url')}")
        print(f"   Instagram: {v.get('instagram')}")
        print(f"   WhatsApp: {v.get('whatsapp')}")
        print(f"   Location: {v.get('location')}")
        print("-" * 40)

print_vendors(plumber_results, "plumber", "Abuja")
print_vendors(electrician_results, "electrician", "Lagos")
print_vendors(cake_results, "cake", "Lagos")
print_vendors(photographer_results, "photographer", "Ibadan")
