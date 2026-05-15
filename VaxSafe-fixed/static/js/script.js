// ============================================================
//  VaxSafe — Main Script
// ============================================================

document.addEventListener("DOMContentLoaded", () => {

    // ---- Sticky Navbar on scroll ----
    window.addEventListener("scroll", () => {
        const navbar = document.querySelector(".navbar");
        if (navbar) {
            navbar.classList.toggle("sticky", window.scrollY > 50);
        }
    });

    // ---- Smooth Scroll for anchor links ----
    document.querySelectorAll("a, .btn").forEach(link => {
        link.addEventListener("click", function (e) {
            if (this.hash && this.hash.startsWith("#")) {
                e.preventDefault();
                const target = document.querySelector(this.hash);
                if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
            }
        });
    });

    // ---- Highlight active nav link ----
    const links = document.querySelectorAll(".nav-links a");
    links.forEach(link => {
        link.addEventListener("click", () => {
            links.forEach(l => l.classList.remove("active"));
            link.classList.add("active");
        });
    });

    // ---- Scroll Reveal ----
    const revealElements = document.querySelectorAll(".reveal");
    const revealOnScroll = () => {
        revealElements.forEach(el => {
            if (el.getBoundingClientRect().top < window.innerHeight - 100) {
                el.classList.add("visible");
            }
        });
    };
    window.addEventListener("scroll", revealOnScroll);
    revealOnScroll();

    // ---- Apply saved language on page load ----
    const saved = localStorage.getItem('vaxsafe_lang');
    if (saved === 'bn') applyLanguage('bn');
});

// ============================================================
//  Language Toggle  (English ↔ বাংলা)
//  Works on ALL pages — called from nav_two.html setLanguage()
// ============================================================
const TRANSLATIONS = {
    "Home": "হোম",
    "Features": "বৈশিষ্ট্যসমূহ",
    "About Us": "আমাদের সম্পর্কে",
    "Contact Us": "যোগাযোগ করুন",
    "Register": "নিবন্ধন",
    "Log In": "লগ ইন",
    "Logout": "লগআউট",
    "Dashboard": "ড্যাশবোর্ড",
    "Schedule": "সময়সূচি",
    "Centers": "কেন্দ্রসমূহ",
    "News": "সংবাদ",
    "Profile": "প্রোফাইল",
    "Language": "ভাষা",
    "Your Health, Future-Proofed.": "আপনার স্বাস্থ্য, ভবিষ্যতের জন্য নিরাপদ।",
    "The intelligent vaccination ecosystem keeping your family safe, one dose at a time.": "পরিবারের সুরক্ষায় বুদ্ধিমান টিকা ব্যবস্থাপনা — একটি ডোজ একটি সময়ে।",
    "Get started": "শুরু করুন",
    "Learn More": "আরও জানুন",
    "Smart Reminders": "স্মার্ট অনুস্মারক",
    "Never miss your next Vaccine": "পরবর্তী টিকার কথা কখনো ভুলবেন না",
    "Family Tracking": "পারিবারিক ট্র্যাকিং",
    "Manage Vaccinations for your loved ones": "প্রিয়জনদের টিকাদান পরিচালনা করুন",
    "Center Finder": "কেন্দ্র খুঁজুন",
    "Locate nearby vaccination centers": "কাছের টিকাদান কেন্দ্র খুঁজুন",
    "Latest Updates": "সর্বশেষ আপডেট",
    "Stay informed with the newest vaccine-related news.": "টিকা সংক্রান্ত সর্বশেষ খবর জানুন।",
    "Secure & Private": "নিরাপদ ও গোপনীয়",
    "Always Available": "সর্বদা উপলব্ধ",
    "For All Users": "সকল ব্যবহারকারীর জন্য",
    "Send Message": "বার্তা পাঠান",
    "Send": "পাঠান",
    "Sign In": "প্রবেশ করুন",
    "Back": "পেছনে যান",
    "Forgot Password?": "পাসওয়ার্ড ভুলে গেছেন?",
    "Don't have an account?": "অ্যাকাউন্ট নেই?",
    "Or log in with": "অথবা লগ ইন করুন",
    "Continue with Google": "Google দিয়ে চালিয়ে যান",
    "Continue with Facebook": "Facebook দিয়ে চালিয়ে যান",
    "Create Account": "অ্যাকাউন্ট তৈরি করুন",
    "Back to Home": "হোমে ফিরুন",
    "Already have an account?": "ইতিমধ্যে অ্যাকাউন্ট আছে?",
    "Upcoming Vaccinations": "আসন্ন টিকাদান",
    "Reminders Active": "সক্রিয় অনুস্মারক",
    "Family Members": "পরিবারের সদস্য",
    "No updates available at the moment.": "এই মুহূর্তে কোনো আপডেট নেই।",
    "Add Vaccine": "টিকা যোগ করুন",
    "Add Family Member": "সদস্য যোগ করুন",
    "Member Name": "সদস্যের নাম",
    "Notification": "বিজ্ঞপ্তি",
    "No family members added yet.": "এখনো কোনো সদস্য যোগ করা হয়নি।",
    "Save Member": "সদস্য সংরক্ষণ",
    "Cancel": "বাতিল",
    "Add Vaccine Record": "টিকার রেকর্ড যোগ করুন",
    "Basic Information": "মৌলিক তথ্য",
    "Vaccine Type": "টিকার ধরন",
    "Dose Number": "ডোজ নম্বর",
    "Date Information": "তারিখের তথ্য",
    "Date Administered/Scheduled": "প্রদান/নির্ধারিত তারিখ",
    "Next Dose Date": "পরবর্তী ডোজের তারিখ",
    "Healthcare Provider": "স্বাস্থ্যসেবা প্রদানকারী",
    "Additional Details": "অতিরিক্ত বিবরণ",
    "Vaccination Center/Hospital": "টিকাদান কেন্দ্র/হাসপাতাল",
    "Batch/Lot Number": "ব্যাচ/লট নম্বর",
    "Manufacturer": "প্রস্তুতকারক",
    "Side Effects": "পার্শ্বপ্রতিক্রিয়া",
    "🏥 Vaccination Centers": "🏥 টিকাদান কেন্দ্রসমূহ",
    "Find nearby vaccination centers in your area": "আপনার এলাকার কাছের টিকাদান কেন্দ্র খুঁজুন",
    "All Cities": "সকল শহর",
    "All Vaccines": "সকল টিকা",
    "Apply Filters": "ফিল্টার প্রয়োগ",
    "Find Nearest": "নিকটতম খুঁজুন",
    "Map View": "মানচিত্র দেখুন",
    "Export List": "তালিকা রপ্তানি",
    "Verified": "যাচাইকৃত",
    "View Details": "বিস্তারিত দেখুন",
    "Get Directions": "দিকনির্দেশনা পান",
    "No Vaccination Centers Found": "কোনো টিকাদান কেন্দ্র পাওয়া যায়নি",
    "Reset Filters": "ফিল্টার রিসেট",
    "24 Hours Open": "২৪ ঘণ্টা খোলা",
    "My Profile": "আমার প্রোফাইল",
    "Profile Information": "প্রোফাইল তথ্য",
    "Not provided": "প্রদান করা হয়নি",
    "Choose File": "ফাইল বেছে নিন",
    "No file chosen": "কোনো ফাইল নেই",
    "Save Changes": "পরিবর্তন সংরক্ষণ",
    "Delete Photo": "ছবি মুছুন",
    "📅 Vaccination Schedule": "📅 টিকাদান সময়সূচি",
    "Manage upcoming doses and health records for your family.": "পরিবারের আসন্ন ডোজ ও স্বাস্থ্য রেকর্ড পরিচালনা করুন।",
    "Edit List": "তালিকা সম্পাদনা",
    "Add Reminder": "অনুস্মারক যোগ করুন",
    "No Records Found": "কোনো রেকর্ড নেই",
    "Your scheduled vaccinations will appear here.": "নির্ধারিত টিকাদান এখানে দেখাবে।",
    "New Appointment": "নতুন অ্যাপয়েন্টমেন্ট",
    "Set a new vaccination reminder": "নতুন টিকাদান অনুস্মারক সেট করুন",
    "Vaccine Name": "টিকার নাম",
    "Notify Via": "বিজ্ঞপ্তি মাধ্যম",
    "Save Schedule": "সময়সূচি সংরক্ষণ",
    "Completed": "সম্পন্ন",
    "Pending": "অপেক্ষমাণ",
    "💉 Vaccination Schedule": "💉 টিকাদান সময়সূচি",
    "Add New Vaccine": "নতুন টিকা যোগ করুন",
    "All Status": "সকল অবস্থা",
    "Scheduled": "নির্ধারিত",
    "Overdue": "বিলম্বিত",
    "All Members": "সকল সদস্য",
    "Upcoming": "আসন্ন",
    "Total Records": "মোট রেকর্ড",
    "Upcoming Vaccines": "আসন্ন টিকাসমূহ",
    "Past Vaccines": "পূর্ববর্তী টিকাসমূহ",
    "days until": "দিন বাকি",
    "No Vaccine Records Yet": "এখনো কোনো রেকর্ড নেই",
    "Add First Vaccine": "প্রথম টিকা যোগ করুন",
    "📰 Health News & Updates": "📰 স্বাস্থ্য সংবাদ ও আপডেট",
    "Stay informed with the latest health and vaccination news": "সর্বশেষ স্বাস্থ্য ও টিকাদান সংবাদ থেকে আপডেট থাকুন",
    "Total Articles": "মোট নিবন্ধ",
    "Featured News": "বৈশিষ্ট্যযুক্ত সংবাদ",
    "All Categories": "সকল বিভাগ",
    "Clear Filters": "ফিল্টার মুছুন",
    "Featured Articles": "বৈশিষ্ট্যযুক্ত নিবন্ধ",
    "Read More": "আরও পড়ুন",
    "All Articles": "সকল নিবন্ধ",
    "No articles found": "কোনো নিবন্ধ নেই",
    "Back to News": "সংবাদে ফিরুন",
    "Summary": "সারসংক্ষেপ",
    "Related Articles": "সম্পর্কিত নিবন্ধ",
    "Latest Vaccine Updates": "সর্বশেষ টিকা আপডেট",
    "All News": "সকল সংবাদ",
    "Add New Update": "নতুন আপডেট",
    "No updates found": "কোনো আপডেট নেই",
    "Back to Updates": "আপডেটে ফিরুন",
    "Edit Update": "আপডেট সম্পাদনা",
    "Verify your Email": "ইমেইল যাচাই করুন",
    "Please enter the OTP sent to your email:": "আপনার ইমেইলে পাঠানো OTP লিখুন:",
    "Enter OTP": "OTP লিখুন",
    "Submit": "জমা দিন",
    "Resend OTP": "OTP পুনরায় পাঠান",
    "All rights reserved.": "সর্বস্বত্ব সংরক্ষিত।",
    "Filter": "ফিল্টার",
    "Export": "রপ্তানি",
    "Apply": "প্রয়োগ",
    "Status": "অবস্থা",
    "Location": "অবস্থান",
    "Notes": "নোট",
    "Age": "বয়স",
    "Date & Time": "তারিখ ও সময়",
    "Scheduled Date": "নির্ধারিত তারিখ",
    "Administered Date": "প্রদানের তারিখ",
    "Next Dose": "পরবর্তী ডোজ",
    "No Vaccine Records Found": "কোনো রেকর্ড পাওয়া যায়নি",
    "General Vaccine News": "সাধারণ টিকা সংবাদ",
    "📌 Important Information": "📌 গুরুত্বপূর্ণ তথ্য",
    "Welcome back! Here's your health overview": "স্বাগতম! এখানে আপনার স্বাস্থ্য সারসংক্ষেপ",
    "Track and manage your family's vaccine records": "পরিবারের টিকার রেকর্ড ট্র্যাক ও পরিচালনা করুন",
};

// Build reverse map (bn → en)
const REVERSE_MAP = {};
for (const [en, bn] of Object.entries(TRANSLATIONS)) {
    REVERSE_MAP[bn] = en;
}

function translateNode(node, toBangla) {
    if (node.nodeType === Node.TEXT_NODE) {
        const text = node.textContent.trim();
        if (!text) return;
        if (toBangla) {
            const bn = TRANSLATIONS[text];
            if (bn) node.textContent = node.textContent.replace(text, bn);
        } else {
            const en = REVERSE_MAP[text];
            if (en) node.textContent = node.textContent.replace(text, en);
        }
    } else if (node.nodeType === Node.ELEMENT_NODE) {
        const tag = node.tagName.toLowerCase();
        if (['script', 'style', 'select'].includes(tag)) return;
        // Translate placeholders
        if (node.hasAttribute('placeholder')) {
            const ph = node.getAttribute('placeholder');
            if (toBangla && TRANSLATIONS[ph]) node.setAttribute('placeholder', TRANSLATIONS[ph]);
            else if (!toBangla && REVERSE_MAP[ph]) node.setAttribute('placeholder', REVERSE_MAP[ph]);
        }
        node.childNodes.forEach(child => translateNode(child, toBangla));
    }
}

function applyLanguage(lang) {
    localStorage.setItem('vaxsafe_lang', lang);
    const toBangla = (lang === 'bn');
    document.body.childNodes.forEach(n => translateNode(n, toBangla));
    // Update language button label
    const btn = document.getElementById('lang-btn');
    if (btn) {
        btn.innerHTML = (lang === 'bn' ? 'বাংলা' : 'English') + ' <span class="dropdown-arrow">▼</span>';
    }
}

// Override the setLanguage function called from nav_two.html
window.setLanguage = function(lang) {
    const code = (lang === 'Bangla' || lang === 'bn') ? 'bn' : 'en';
    applyLanguage(code);
    const dropdown = document.getElementById('lang-dropdown');
    if (dropdown) dropdown.classList.remove('show');
    const btn = document.getElementById('lang-btn');
    if (btn) {
        const arrow = btn.querySelector('.dropdown-arrow');
        if (arrow) arrow.style.transform = 'rotate(0deg)';
    }
};