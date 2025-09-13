import pandas as pd

def create_detailed_view(df_original: pd.DataFrame) -> pd.DataFrame:
    """
    [독립 기능 1] 원본 데이터를 받아 '상세 뷰'를 생성한다.
    (중복 제거 -> 그룹핑 -> 정렬)
    """
    # 1. 중복 제거
    df_deduplicated = df_original.drop_duplicates(subset=['과제고유번호'], keep='first')

    # 2. 그룹핑 로직
    df = df_deduplicated.copy()
    df['GroupID_temp'] = df.groupby('(기관)세부과제번호').ngroup()
    df['GroupID'] = df['GroupID_temp'].apply(lambda x: x if x != -1 else pd.NA)
    df = df.drop(columns=['GroupID_temp'])
    task_to_group = pd.Series(df.과제고유번호.values, index=df.과제고유번호).to_dict()
    for index, row in df.iterrows():
        prev_task_id_str = row.get('이전과제고유번호')
        current_task_id = row.get('과제고유번호')
        if pd.notna(prev_task_id_str) and current_task_id in task_to_group:
            current_group = task_to_group[current_task_id]
            if pd.isna(current_group): continue
            prev_task_ids = str(prev_task_id_str).split(';')
            for prev_task_id in prev_task_ids:
                prev_task_id = prev_task_id.strip()
                if prev_task_id in task_to_group:
                    prev_group = task_to_group[prev_task_id]
                    if pd.notna(prev_group) and prev_group != current_group:
                        df.loc[df['GroupID'] == current_group, 'GroupID'] = prev_group
                        for task, group in task_to_group.items():
                            if group == current_group: task_to_group[task] = prev_group
    ungrouped_mask = df['GroupID'].isna()
    if ungrouped_mask.any():
        existing_groups = df['GroupID'].dropna().astype(int)
        start_num = existing_groups.max() + 1 if not existing_groups.empty else 0
        df.loc[ungrouped_mask, 'GroupID'] = range(start_num, start_num + ungrouped_mask.sum())
    df['GroupID'] = df['GroupID'].astype(int)
    if 'NO' in df.columns: df = df.drop(columns=['NO'])
    cols = ['GroupID'] + [col for col in df.columns if col != 'GroupID']
    df = df[cols]

    # 3. 정렬
    df_detailed = df.sort_values(by=['GroupID', '기준년도']).reset_index(drop=True)
    return df_detailed


def create_summary_view(df_original: pd.DataFrame) -> pd.DataFrame:
    """
    [독립 기능 2] 원본 데이터를 받아 확정된 구성안의 '요약 뷰'를 생성한다.
    이 함수는 다른 함수를 호출하지 않고 모든 것을 스스로 처리한다.
    """
    # 1. 중복 제거 및 그룹핑 (내부적으로 직접 수행)
    df_grouped = create_detailed_view(df_original)

    # 2. '최근 5년' 범위 확정
    latest_year = df_grouped['기준년도'].max()
    year_range = range(latest_year - 4, latest_year + 1)

    # 3. 컬럼 목록 정의
    # (a) 연도별로 확장할 3가지 핵심 연구비
    PIVOT_COLS = ['정부투자연구비', '민간연구비_소계', '연구비합계']

    # (b) '요약 뷰'에서 아예 제외할, 불필요한 모든 세부 연구비 목록
    EXCLUDE_BUDGET_COLS = [
        '인건비_현금', '인건비_현물', '직접비_현금', '직접비_현물', '간접비', '위탁연구비',
        '청관련물건비', '민간연구비_지방정부현금', '민간연구비_지방정부현물', '민간연구비_대학현금',
        '민간연구비_대학현물', '민간연구비_대기업현금', '민간연구비_대기업현물',
        '민간연구비_중견기업현금', '민간연구비_중견기업현물', '민간연구비_중소기업현금',
        '민간연구비_중소기업현물', '민간연구비_병원현금', '민간연구비_병원현물',
        '민간연구비_기타현금', '민간연구비_기타현물'
    ]

    # (c) 대표값으로 사용할 '고정 정보' 컬럼 자동 생성
    ALL_BUDGET_COLS_TO_EXCLUDE = PIVOT_COLS + EXCLUDE_BUDGET_COLS
    STATIC_COLS_TO_EXCLUDE = ['GroupID', '기준년도'] + ALL_BUDGET_COLS_TO_EXCLUDE
    static_cols = [col for col in df_grouped.columns if col not in STATIC_COLS_TO_EXCLUDE]

    # 4. 각 파트별 데이터 생성
    # (a) 고정 정보 (대표값)
    agg_rules_static = {col: 'last' for col in static_cols}
    df_static = df_grouped.groupby('GroupID').agg(agg_rules_static).reset_index()

    # (b) 추가 정보 (최신 기준년도, 총 연구비합계)
    df_extra_info = df_grouped.groupby('GroupID').agg(
        최신_기준년도=('기준년도', 'max'),
        총_연구비합계=('연구비합계', 'sum')
    ).reset_index()

    # (c) 연도별 확장 정보 (오직 3가지 핵심 연구비만, 최근 5년)
    df_filtered = df_grouped[df_grouped['기준년도'].isin(year_range)]
    df_pivot = pd.DataFrame(index=df_grouped['GroupID'].unique())
    existing_pivot_cols = [col for col in PIVOT_COLS if col in df_filtered.columns]
    if not df_filtered.empty and existing_pivot_cols:
        df_pivot = df_filtered.pivot(index='GroupID', columns='기준년도', values=existing_pivot_cols)
        df_pivot.columns = [f'{col[0]} {col[1]}' for col in df_pivot.columns]
        df_pivot = df_pivot.reset_index()

    # 5. 모든 파트 순서대로 병합
    df_summary = pd.merge(df_static, df_extra_info, on='GroupID', how='left')
    if not df_pivot.empty:
        df_summary = pd.merge(df_summary, df_pivot, on='GroupID', how='left')

    return df_summary