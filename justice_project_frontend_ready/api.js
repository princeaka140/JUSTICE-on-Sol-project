// app.js (final)
const API_BASE = "http://127.0.0.1:5000";  // change to your backend host

// Simple fetch wrapper (no auto user_id injection)
async function apiFetch(endpoint, options = {}) {
  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      method: options.method || "GET",
      headers: {
        "Content-Type": "application/json",
      },
      body: options.body ? JSON.stringify(options.body) : undefined,
    });

    if (!res.ok) {
      throw new Error(`API error ${res.status}`);
    }

    return await res.json();
  } catch (err) {
    console.error("Fetch error:", err);
    return null;
  }
}

// ✅ Get referral stats
async function fetchReferralStats(userId) {
  return await apiFetch(`/referral/stats?user_id=${userId}`);
}

// ✅ Get leaderboard
async function fetchLeaderboard() {
  return await apiFetch(`/referral/leaderboard`);
}

// ✅ Generate referral link
async function generateReferralLink(userId) {
  return `${window.location.origin}/register?ref=${userId}`;
}

// ✅ Record referral click
async function recordReferralClick(userId, referrerId) {
  return await apiFetch(`/referral/click?user_id=${userId}&referrer=${referrerId}`, { method: "POST" });
}

// ✅ Record successful registration
async function recordReferralRegister(userId, referrerId) {
  return await apiFetch(`/referral/register?user_id=${userId}&referrer=${referrerId}`, { method: "POST" });
}

// Expose globally for frontend HTML
window.ReferralAPI = {
  fetchReferralStats,
  fetchLeaderboard,
  generateReferralLink,
  recordReferralClick,
  recordReferralRegister
};
