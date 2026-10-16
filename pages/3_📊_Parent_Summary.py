from __future__ import annotations

import re
import streamlit as st

st.set_page_config(page_title="Parent Progress Summary 📊", page_icon="📊", layout="centered")

st.title("📊 Parent Summary & Assessment Tracker")
st.caption("A quick overview of your child's dictation accuracy, mastered vocabulary, and revision queues.")

# Retrieve Session State
raw_words = st.session_state.get("raw_words", "")
mastered = st.session_state.get("mastered_words", set())
unfamiliar = st.session_state.get("unfamiliar_words", set())

full_word_list = [line.strip() for line in raw_words.replace("，", "\n").replace(",", "\n").splitlines() if line.strip()]
total_words = len(full_word_list)

if total_words == 0:
    st.info("👆 No active spelling list found. Add a weekly list on the Home page to start tracking progress!")
    st.stop()

# Key Progress Metrics using Native Streamlit Metrics
st.subheader("📈 Overall Performance Metrics")

cols = st.columns(3)
with cols[0]:
    with st.container(border=True):
        st.metric(label="Total Words", value=total_words)

with cols[1]:
    with st.container(border=True):
        st.metric(label="Mastered (🌟)", value=len(mastered))

with cols[2]:
    with st.container(border=True):
        st.metric(label="Needs Practice (🔴)", value=len(unfamiliar))

# Progress Bar
completion_rate = (len(mastered) / total_words) if total_words > 0 else 0.0
st.progress(completion_rate, text=f"Mastery Progress: {int(completion_rate * 100)}%")

st.divider()

# Itemized Breakdown
st.subheader("📋 Word Breakdown & Status")

col_a, col_b = st.columns(2)

with col_a:
    st.markdown("### 🌟 Mastered Words")
    if mastered:
        for word in sorted(mastered):
            st.success(f"✅ {word}")
    else:
        st.caption("No words marked as mastered yet.")

with col_b:
    st.markdown("### 🔴 Words Needing Practice")
    if unfamiliar:
        for word in sorted(unfamiliar):
            st.error(f"❌ {word}")
    else:
        st.caption("Great job! No tricky words flagged right now.")

st.divider()

# Actionable Study Plan Guidance for Parents
st.subheader("💡 Recommended Home Study Plan")

if len(unfamiliar) > 0:
    st.warning(f"**Focus Area:** Your child needs extra practice on **{len(unfamiliar)} word(s)**.")
    st.markdown("""
    * **Targeted Revision:** Go to the **Dictation Quiz** page and select **'🔴 Practice Unfamiliar Only'**.
    * **Stroke Order Check:** For Chinese characters in the review list, open the **Learn Words** page to review character animations together.
    * **Phonics & Visual Association:** Focus on breaking tricky English words into syllables before dictation.
    """)
elif len(mastered) == total_words:
    st.success("🎉 **Outstanding Result!** Your child has mastered all the words in this week's list. Ready for school dictation!")
else:
    st.info("💡 Start the **Dictation Quiz** to evaluate which words your child knows well and which ones need review.")
