import streamlit as st
import pandas as pd
import numpy as np
import io
from datetime import datetime
st.title("📊 Conflict & Attendance Analysis")
st.write("""
Upload the **Excel file** to analyze student conflicts between **Physical** and **Connect** sessions.  
This tool provides:
- Conflict analysis for **L1** and **L2**
- Attendance breakdown (Present/Absent)
- Conflict analysis by **Governorate**
 This application was developed by **Abdelrahman Salah**.
Designed for the **Connect** and **Physical** teams.
Part of Almentor
""")

uploaded_file = st.file_uploader("Upload the Excel file", type=["xlsx"])
if uploaded_file:
   xls = pd.ExcelFile(uploaded_file)

   physical_sessions = pd.read_excel(xls, sheet_name='Physical Sessions')
   connect_sessions_l1 = pd.read_excel(xls, sheet_name='Connect Sessions L1')
   connect_sessions_l2 = pd.read_excel(xls, sheet_name='Connect Sessions L2')

   for df in [physical_sessions, connect_sessions_l1, connect_sessions_l2]:
       df["Event Start Date"] = pd.to_datetime(df["Event Start Date"])
       df["Weekday"] = df["Event Start Date"].dt.day_name()
       df["Event Start Time"] = df["Event Start Date"].dt.strftime("%H:%M:%S")
       df["Event Start Time"] = pd.to_datetime(df["Event Start Time"], format="%H:%M:%S", errors="coerce").dt.time

   def find_conflicts(connect_sessions, physical_sessions, level):
       conflicts = []
       for _, row in connect_sessions.iterrows():
           username = row["Username"]
           connect_day = row["Weekday"]
           connect_time = row["Event Start Time"]
           connect_attendance = row["Event Attendance (Status)"]
           physical_info = physical_sessions[physical_sessions["Username"] == username]
           if not physical_info.empty:
               physical_row = physical_info.iloc[0]
               physical_day = physical_row["Weekday"]
               physical_time = physical_row["Event Start Time"]
               physical_attendance = physical_row["Event Attendance (Status)"]
               governorate = physical_row["Governorate En"]

               if connect_day == physical_day:
                   time_diff = abs((datetime.combine(datetime.today(), connect_time) -
                                    datetime.combine(datetime.today(), physical_time)).total_seconds()) / 3600
                   if time_diff < 2.5:
                       conflicts.append({
                           "Username": username,
                           "Governorate": governorate,
                           "Connect Session": row["Session Code"],
                           "Physical Session": physical_row["Session Code"],
                           "Weekday": connect_day,
                           "Connect Time": connect_time,
                           "Physical Time": physical_time,
                           "Time Difference (hrs)": round(time_diff, 2),
                           "Conflict": "True",
                           "Connect Attendance": connect_attendance,
                           "Physical Attendance": physical_attendance
                       })
       return pd.DataFrame(conflicts)
   
   conflicts_l1 = find_conflicts(connect_sessions_l1, physical_sessions, "L1")
   conflicts_l2 = find_conflicts(connect_sessions_l2, physical_sessions, "L2")
 
   def analyze_attendance(conflicts):
       total_conflicts = len(conflicts)
       attended_connect = conflicts[(conflicts["Connect Attendance"] == "Present") &
                                    (conflicts["Physical Attendance"] == "Absent")].shape[0]
       attended_physical = conflicts[(conflicts["Connect Attendance"] == "Absent") &
                                     (conflicts["Physical Attendance"] == "Present")].shape[0]
       attended_both = conflicts[(conflicts["Connect Attendance"] == "Present") &
                                 (conflicts["Physical Attendance"] == "Present")].shape[0]
       return {
           "Total Conflicts": total_conflicts,
           "Attended Connect Only": attended_connect,
           "Attended Physical Only": attended_physical,
           "Attended Both": attended_both
       }

   conflict_by_gov = conflicts_l1.groupby("Governorate").size().reset_index(name="L1 Conflicts")
   conflict_by_gov_l2 = conflicts_l2.groupby("Governorate").size().reset_index(name="L2 Conflicts")
   conflict_by_gov = conflict_by_gov.merge(conflict_by_gov_l2, on="Governorate", how="outer").fillna(0)

   st.write("## 🛑 Conflicts L1")
   st.dataframe(conflicts_l1)
   st.write("## 🛑 Conflicts L2")
   st.dataframe(conflicts_l2)
   st.write("## 📊 Conflict Analysis by Governorate")
   st.dataframe(conflict_by_gov)

   attendance_analysis_l1 = analyze_attendance(conflicts_l1)
   attendance_analysis_l2 = analyze_attendance(conflicts_l2)
   attendance_df = pd.DataFrame([
       {"Category": "Total Conflicts", "L1": attendance_analysis_l1["Total Conflicts"], "L2": attendance_analysis_l2["Total Conflicts"]},
       {"Category": "Attended Connect Only", "L1": attendance_analysis_l1["Attended Connect Only"], "L2": attendance_analysis_l2["Attended Connect Only"]},
       {"Category": "Attended Physical Only", "L1": attendance_analysis_l1["Attended Physical Only"], "L2": attendance_analysis_l2["Attended Physical Only"]},
       {"Category": "Attended Both", "L1": attendance_analysis_l1["Attended Both"], "L2": attendance_analysis_l2["Attended Both"]}
   ])
   st.write("## 🎯 Attendance Analysis")
   st.dataframe(attendance_df)

   output_buffer = io.BytesIO()
   with pd.ExcelWriter(output_buffer, engine='xlsxwriter') as writer:
       conflicts_l1.to_excel(writer, sheet_name="Conflicts L1", index=False)
       conflicts_l2.to_excel(writer, sheet_name="Conflicts L2", index=False)
       conflict_by_gov.to_excel(writer, sheet_name="Conflict By Governorate", index=False)
       attendance_df.to_excel(writer, sheet_name="Attendance Analysis", index=False)
   output_buffer.seek(0)

   st.download_button(
       label="📥 Download Conflict & Attendance Analysis",
       data=output_buffer,
       file_name="conflict_attendance_analysis.xlsx",
       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
   )