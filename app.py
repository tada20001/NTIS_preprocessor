import streamlit as st
import pandas as pd
from io import BytesIO
# utils.py 파일에서 우리가 만든 두 개의 독립적인 함수를 불러옵니다.
from utils import create_detailed_view, create_summary_view

# --- 웹 페이지 기본 설정 ---
st.set_page_config(layout="wide")
st.title("NTIS 과제 데이터 전처리기")

# --- 탭(Tabs) UI 생성 ---
tab1, tab2 = st.tabs(["상세 뷰 (연차별)", "요약 뷰 (그룹별 재구성)"])

# ==============================================================================
#  [독립 기능 1] 상세 뷰 탭
# ==============================================================================
with tab1:
    st.header("상세 뷰 (연차별)")
    st.write("각 과제의 연차별 데이터가 모두 표시됩니다. (실무 분석가용)")

    # --- 상세 뷰 탭을 위한 독립적인 파일 업로더 ---
    detailed_uploader = st.file_uploader(
        "상세 뷰 생성을 위한 NTIS 엑셀 파일을 업로드하세요.",
        type=["xlsx", "xls"],
        key="detailed_uploader"  # 각 업로더를 구분하기 위한 고유 키
    )

    if detailed_uploader is not None:
        try:
            st.info("상세 뷰 데이터를 생성하고 있습니다...")
            df_original_detailed = pd.read_excel(detailed_uploader, engine='openpyxl')

            # 상세 뷰 생성 함수 호출
            df_detailed = create_detailed_view(df_original_detailed.copy())
            st.success("상세 뷰 데이터 생성 완료!")

            # --- 이 탭 안에서만 사용되는 처리 결과 요약 ---
            st.subheader("처리 결과 요약 (상세 뷰 기준)")
            total_original_rows = len(df_original_detailed)
            removed_count = len(df_original_detailed) - len(df_original_detailed.drop_duplicates(subset=['과제고유번호']))
            total_groups = df_detailed['GroupID'].nunique()
            col1, col2, col3 = st.columns(3)
            with col1: st.metric("원본 데이터 행 수", f"{total_original_rows} 개")
            with col2: st.metric("제거된 중복 행 수", f"{removed_count} 개")
            with col3: st.metric("그룹핑된 최종 과제 수", f"{total_groups} 개")

            # --- 상세 뷰 탭 내 알고리즘 설명 ---
            with st.expander("ℹ️ 이 데이터의 처리 기준 보기"):
                st.markdown("""
                - **중복 제거**: `'과제고유번호'`가 동일한 행은 첫 번째 행만 남기고 제거합니다.
                - **그룹핑**: `' (기관)세부과제번호'`와 `'이전과제고유번호'`를 기준으로 연관 과제를 하나의 그룹으로 묶습니다.
                """)

            st.dataframe(df_detailed)

            # --- 상세 뷰 탭을 위한 독립적인 다운로드 버튼 ---
            @st.cache_data
            def convert_df_to_excel_detailed(df):
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='detailed_view')
                return output.getvalue()
            excel_data_detailed = convert_df_to_excel_detailed(df_detailed)
            st.download_button(
                label="상세 뷰 엑셀 파일 다운로드",
                data=excel_data_detailed,
                file_name="ntis_detailed_view.xlsx"
            )
        except Exception as e:
            st.error(f"상세 뷰 처리 중 오류 발생: {e}")
            st.exception(e)

# ==============================================================================
#  [독립 기능 2] 요약 뷰 탭
# ==============================================================================
with tab2:
    st.header("요약 뷰 (그룹별 재구성)")
    st.write("각 과제 그룹의 정보가 하나의 행으로 재구성됩니다. (보고 및 의사결정용)")

    # --- 요약 뷰 탭을 위한 독립적인 파일 업로더 ---
    summary_uploader = st.file_uploader(
        "요약 뷰 생성을 위한 NTIS 엑셀 파일을 업로드하세요.",
        type=["xlsx", "xls"],
        key="summary_uploader" # 각 업로더를 구분하기 위한 고유 키
    )

    if summary_uploader is not None:
        try:
            st.info("요약 뷰 데이터를 생성하고 있습니다...")
            df_original_summary = pd.read_excel(summary_uploader, engine='openpyxl')

            # 요약 뷰 생성 함수 호출
            df_summary = create_summary_view(df_original_summary.copy())
            st.success("요약 뷰 데이터 생성 완료!")

            # --- 이 탭 안에서만 사용되는 처리 결과 요약 ---
            st.subheader("처리 결과 요약 (요약 뷰 기준)")
            total_original_rows_sum = len(df_original_summary)
            removed_count_sum = len(df_original_summary) - len(df_original_summary.drop_duplicates(subset=['과제고유번호']))
            total_groups_sum = df_summary['GroupID'].nunique()
            col1_sum, col2_sum, col3_sum = st.columns(3)
            with col1_sum: st.metric("원본 데이터 행 수", f"{total_original_rows_sum} 개")
            with col2_sum: st.metric("제거된 중복 행 수", f"{removed_count_sum} 개")
            with col3_sum: st.metric("그룹핑된 최종 과제 수", f"{total_groups_sum} 개")

            # --- 요약 뷰 탭 내 알고리즘 설명 ---
            with st.expander("ℹ️ 이 데이터의 처리 기준 보기"):
                st.markdown("""
                - **중복 제거 및 그룹핑**: '상세 뷰'와 동일한 기준으로 처리됩니다.
                - **재구성**: 그룹핑된 데이터를 기준으로, 3가지 핵심 연구비(`정부투자연구비`, `민간연구비_소계`, `연구비합계`)는 연도별 컬럼으로 확장되고, `총_연구비합계`가 추가되며, 나머지 정보는 최신 연도 값으로 대표됩니다.
                """)

            st.dataframe(df_summary)

            # --- 요약 뷰 탭을 위한 독립적인 다운로드 버튼 ---
            @st.cache_data
            def convert_df_to_excel_summary(df):
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='summary_view')
                return output.getvalue()
            excel_data_summary = convert_df_to_excel_summary(df_summary)
            st.download_button(
                label="요약 뷰 엑셀 파일 다운로드",
                data=excel_data_summary,
                file_name="ntis_summary_view.xlsx"
            )
        except Exception as e:
            st.error(f"요약 뷰 처리 중 오류 발생: {e}")
            st.exception(e)