#include <windows.h>

#include <algorithm>
#include <cstdarg>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include <MinHook.h>
#include <PluginAPI.h>

namespace {

struct GameString {
    union {
        wchar_t local[8];
        const wchar_t *heap;
    };
    size_t size;
    size_t capacity;
};
static_assert(sizeof(GameString) == 32, "GameString must match MSVC's std::wstring");

struct SharedNode {
    uint8_t *node;
    void *control;
};

struct GameColumn {
    uint8_t unknown0[8];
    uint8_t *items;
    uint8_t unknown10[8];
    int64_t itemCount;
};
static_assert(sizeof(GameColumn) == 32, "GameColumn must be 0x20 bytes");

using ConstructorFn = void *(__fastcall *)(void *screen, void *arg);
using InputFrameFn = void(__fastcall *)(void *screen, void *input, float delta);
using MoveColumnFn = void(__fastcall *)(void *screen, int direction);
using InstantiateFn = SharedNode *(__fastcall *)(void *screen, SharedNode *out, const wchar_t *parent,
                                                 const wchar_t *templateName);
using FindNodeFn = SharedNode *(__fastcall *)(void *screen, SharedNode *out, const GameString *name);
using SetTextFn = void(__fastcall *)(void *button, const GameString *text);
using TextFieldSetTextFn = void(__fastcall *)(void *textField, const wchar_t *text, int flags);
using DynamicCastFn = void *(__cdecl *)(void *object, long vfDelta, void *sourceType, void *targetType,
                                        int isReference);

struct GameFunction {
    const char *name;
    uintptr_t rva;
    const char *prologue;
};

const GameFunction kConstructor = {"constructor", 0x8B4280, "48895c24185556574154415541564157"};
const GameFunction kInputFrame = {"input frame", 0x8B9380, "488bc448895818488970205557415441"};
const GameFunction kMoveColumn = {"move column", 0x8BA240, "48895c2410488974241848897c242055"};
const GameFunction kInstantiate = {"instantiate", 0x8454B0, "4055535657415441564157488d6c24d9"};
const GameFunction kFindNode = {"find node", 0x839FD0, "48895c24084889742410574883ec4048"};
const GameFunction kSetText = {"set text", 0x83B880, "48895c2408574883ec30488bda488b91"};
const GameFunction kTextFieldSetText = {"text field set text", 0x7F8BB0, "48895c24184889742420555741544156"};
const GameFunction kDynamicCast = {"dynamic cast", 0x12DA7AA, "ff25"};
constexpr uintptr_t kComponentTypeRva = 0x2062F00;
constexpr uintptr_t kButtonTypeRva = 0x2062F50;
constexpr uintptr_t kTextFieldTypeRva = 0x2062F28;
constexpr const char kComponentTypeName[] = ".?AVComponent@ui@@";
constexpr const char kButtonTypeName[] = ".?AVHUiButton@ui@@";
constexpr const char kTextFieldTypeName[] = ".?AVTextField@ui@@";

constexpr ptrdiff_t kCategoryNames = 0x7D8;
constexpr ptrdiff_t kCategoryNamesEnd = 0x7E0;
constexpr ptrdiff_t kCategoryCount = 0xE4E8;
constexpr ptrdiff_t kColumns = 0xE500;
constexpr ptrdiff_t kColumnCount = 0xE510;
constexpr ptrdiff_t kCurrentColumn = 0xE548;
constexpr ptrdiff_t kNodePosition = 0x1A0;
constexpr ptrdiff_t kNodeArea = 0x1B0;
constexpr ptrdiff_t kButtonText = 0x220;
constexpr ptrdiff_t kScrollX = 0x210;

constexpr int kMoveLeft = 0;
constexpr int kMoveRight = 1;
constexpr int kMaxTabs = 32;
constexpr int kRows = 2;

constexpr wchar_t kTabParent[] = L"BaseFrame";
constexpr wchar_t kTabTemplate[] = L"WeaponSel_IndexBase";
constexpr wchar_t kListNode[] = L"WindowUpper";
constexpr wchar_t kStatsNode[] = L"WeaponLevel";
constexpr wchar_t kHighlightTemplate[] = L"SelectCursor";
constexpr wchar_t kLabelTemplate[] = L"WeaponLevelIndex";
constexpr wchar_t kColumnArea[] = L"WeaponSelectArea";
constexpr wchar_t kColumnTemplate[] = L"WeaponColumns";

constexpr float kUiWidth = 1920.0f;
constexpr float kUiHeight = 1080.0f;
constexpr float kTabHeight = 39.0f;
constexpr float kTabGap = 6.0f;
constexpr float kRowGap = 6.0f;
constexpr float kListGap = 8.0f;
constexpr float kTextPadding = 14.0f;
constexpr float kLargestFont = 24.0f;
constexpr float kSmallestFont = 16.0f;
constexpr float kCharWidthPerFontPixel = 0.53f;
constexpr float kMarkHeight = 3.0f;
constexpr float kTabTextInset = 16.0f;
constexpr float kLabelSlack = 4.0f;
constexpr float kHidden = -4000.0f;

constexpr ULONGLONG kForegroundGraceMs = 8000;

struct Tab {
    uint8_t *node = nullptr;
    uint8_t *button = nullptr;
    float x = 0;
    float y = 0;
    float width = 0;
    float height = 0;
};

uint8_t *gameBase = nullptr;
ConstructorFn originalConstructor = nullptr;
InputFrameFn originalInputFrame = nullptr;
MoveColumnFn moveColumn = nullptr;
InstantiateFn instantiate = nullptr;
FindNodeFn findNode = nullptr;
SetTextFn setText = nullptr;
DynamicCastFn dynamicCast = nullptr;
TextFieldSetTextFn textFieldSetText = nullptr;

void *activeScreen = nullptr;
std::vector<Tab> tabs;
std::vector<std::wstring> tabLabels;
Tab indicator;
std::vector<uint8_t *> marks;
uint8_t *highlight = nullptr;
uint8_t *label = nullptr;
uint8_t *labelText = nullptr;
uint8_t *columnArea = nullptr;
float columnWidth = 0;
float tabFontSize = kLargestFont;
int shownColumn = -1;
uint32_t shownVisible = 0;

std::string GamePath(const char *file) {
    char path[MAX_PATH];
    DWORD length = GetModuleFileNameA(nullptr, path, MAX_PATH);
    std::string dir(path, length);
    return dir.substr(0, dir.find_last_of("\\/") + 1) + file;
}

void Log(const char *message) {
    FILE *fh = nullptr;
    if (fopen_s(&fh, GamePath("EDF6UI.log").c_str(), "a") == 0 && fh) {
        SYSTEMTIME t;
        GetLocalTime(&t);
        fprintf(fh, "[%02d:%02d:%02d] %s\n", t.wHour, t.wMinute, t.wSecond, message);
        fclose(fh);
    }
}

void LogF(const char *fmt, ...) {
    char buf[2048];
    va_list args;
    va_start(args, fmt);
    vsnprintf(buf, sizeof(buf), fmt, args);
    va_end(args);
    Log(buf);
}

std::string Utf8(const std::wstring &text) {
    int length = WideCharToMultiByte(CP_UTF8, 0, text.c_str(), (int)text.size(), nullptr, 0, nullptr, nullptr);
    std::string out(length, '\0');
    WideCharToMultiByte(CP_UTF8, 0, text.c_str(), (int)text.size(), out.data(), length, nullptr, nullptr);
    return out;
}

template <typename T> T &Field(void *object, ptrdiff_t offset) {
    return *reinterpret_cast<T *>(static_cast<uint8_t *>(object) + offset);
}

GameString GameStringView(const std::wstring &text) {
    GameString view{};
    view.size = text.size();
    if (text.size() < 8) {
        wmemcpy(view.local, text.c_str(), text.size() + 1);
        view.capacity = 7;
    } else {
        view.heap = text.c_str();
        view.capacity = text.size();
    }
    return view;
}

std::wstring FromGameString(const GameString &text) {
    return std::wstring(text.capacity >= 8 ? text.heap : text.local, text.size);
}

void Release(void *control) {
    if (!control) {
        return;
    }
    auto uses = reinterpret_cast<volatile LONG *>(static_cast<uint8_t *>(control) + 8);
    auto weaks = reinterpret_cast<volatile LONG *>(static_cast<uint8_t *>(control) + 12);
    auto vtable = *reinterpret_cast<void (***)(void *)>(control);
    if (InterlockedDecrement(uses) == 0) {
        vtable[0](control);
        if (InterlockedDecrement(weaks) == 0) {
            vtable[1](control);
        }
    }
}

bool MatchesPrologue(const GameFunction &function) {
    const uint8_t *code = gameBase + function.rva;
    const size_t length = strlen(function.prologue) / 2;
    for (size_t i = 0; i < length; i++) {
        unsigned int value = 0;
        sscanf_s(function.prologue + 2 * i, "%2x", &value);
        if (code[i] != value) {
            LogF("EDF.dll+0x%llX (%s) doesn't have the expected bytes; tabs disabled",
                 (unsigned long long)function.rva, function.name);
            return false;
        }
    }
    return true;
}

bool MatchesTypeName(uintptr_t rva, const char *name) {
    if (strcmp(reinterpret_cast<const char *>(gameBase + rva + 16), name) == 0) {
        return true;
    }
    LogF("no type %s at EDF.dll+0x%llX; tabs disabled", name, (unsigned long long)rva);
    return false;
}

int CategoryCount(void *screen) {
    const int count = Field<int>(screen, kCategoryCount);
    const auto names = Field<GameString *>(screen, kCategoryNames);
    const auto namesEnd = Field<GameString *>(screen, kCategoryNamesEnd);
    const int columns = (int)Field<int64_t>(screen, kColumnCount);
    int usable = count;
    if (names && namesEnd >= names && namesEnd - names < usable) {
        usable = (int)(namesEnd - names);
    }
    if (columns < usable) {
        usable = columns;
    }
    return usable < 0 ? 0 : (usable > kMaxTabs ? kMaxTabs : usable);
}

int64_t ItemCount(void *screen, int column) {
    return Field<GameColumn *>(screen, kColumns)[column].itemCount;
}

int CurrentColumn(void *screen) {
    return Field<int>(screen, kCurrentColumn);
}

uint8_t *FindNode(void *screen, const wchar_t *name) {
    const std::wstring text(name);
    const GameString view = GameStringView(text);
    SharedNode found{};
    findNode(screen, &found, &view);
    Release(found.control);
    return found.node;
}

uint8_t *CreateNode(void *screen, const wchar_t *templateName) {
    SharedNode created{};
    instantiate(screen, &created, kTabParent, templateName);
    Release(created.control);
    return created.node;
}

void *CastNode(uint8_t *node, uintptr_t typeRva) {
    return node ? dynamicCast(node, 0, gameBase + kComponentTypeRva, gameBase + typeRva, 0) : nullptr;
}

void PlaceNode(uint8_t *node, float x, float y, float width, float height) {
    if (!node) {
        return;
    }
    float *position = &Field<float>(node, kNodePosition);
    position[0] = x;
    position[1] = y;
    float *area = &Field<float>(node, kNodeArea);
    area[2] = width;
    area[3] = height;
}

Tab CreateTab(void *screen) {
    Tab tab;
    tab.node = CreateNode(screen, kTabTemplate);
    if (tab.node) {
        tab.button = static_cast<uint8_t *>(CastNode(tab.node, kButtonTypeRva));
    }
    return tab;
}

uint8_t *TabText(const Tab &tab) {
    return tab.button ? Field<uint8_t *>(tab.button, kButtonText) : nullptr;
}

void PlaceTab(Tab &tab, float x, float y, float width, float height) {
    tab.x = x;
    tab.y = y;
    tab.width = width;
    tab.height = height;
    PlaceNode(tab.node, x, y, width, height);
    if (uint8_t *text = TabText(tab)) {
        Field<float>(text, kNodeArea + 8) = width - 2 * kTextPadding;
    }
}

void SetTabText(const Tab &tab, const std::wstring &text) {
    if (!tab.button) {
        return;
    }
    const GameString view = GameStringView(text);
    setText(tab.button, &view);
}

std::wstring TabLabel(void *screen, int column) {
    const GameString &name = Field<GameString *>(screen, kCategoryNames)[column];
    return FromGameString(name) + L"  " + std::to_wstring(ItemCount(screen, column));
}

std::wstring IndicatorLabel(void *screen) {
    return L"← " + std::to_wstring(CurrentColumn(screen) + 1) + L" / " +
           std::to_wstring(tabs.size()) + L" →";
}

float NaturalWidth(const std::wstring &label, float fontSize) {
    return label.size() * kCharWidthPerFontPixel * fontSize + 2 * kTextPadding;
}

struct RowPlan {
    float fontSize = kSmallestFont;
    int split = 0;
    std::vector<float> widths;
    float indicatorWidth = 0;
};

float RowLength(const RowPlan &plan, int from, int to, bool withIndicator) {
    float length = 0;
    int items = 0;
    for (int i = from; i < to; i++, items++) {
        length += plan.widths[i];
    }
    if (withIndicator) {
        length += plan.indicatorWidth;
        items++;
    }
    return length + (items > 1 ? (items - 1) * kTabGap : 0);
}

RowPlan PlanRows(const std::vector<std::wstring> &labels, const std::wstring &indicatorLabel, float fontSize,
                 float &longestRow) {
    RowPlan plan;
    plan.fontSize = fontSize;
    for (const std::wstring &label : labels) {
        plan.widths.push_back(NaturalWidth(label, fontSize));
    }
    plan.indicatorWidth = NaturalWidth(indicatorLabel, fontSize);
    const int count = (int)labels.size();
    longestRow = 1e9f;
    for (int split = 1; split <= count; split++) {
        const float first = RowLength(plan, 0, split, false);
        const float second = RowLength(plan, split, count, true);
        const float longest = first > second ? first : second;
        if (longest < longestRow) {
            longestRow = longest;
            plan.split = split;
        }
    }
    return plan;
}

RowPlan ChooseRows(const std::vector<std::wstring> &labels, const std::wstring &indicatorLabel, float rowWidth) {
    float longest = 0;
    for (float fontSize = kLargestFont; fontSize > kSmallestFont; fontSize -= 1) {
        RowPlan plan = PlanRows(labels, indicatorLabel, fontSize, longest);
        if (longest <= rowWidth) {
            return plan;
        }
    }
    return PlanRows(labels, indicatorLabel, kSmallestFont, longest);
}

void PlaceRow(const std::vector<Tab *> &row, std::vector<float> widths, float left, float rowWidth, float y,
              bool lastIsIndicator) {
    if (row.empty()) {
        return;
    }
    const float gaps = (row.size() - 1) * kTabGap;
    float natural = 0;
    for (float width : widths) {
        natural += width;
    }
    const float free = rowWidth - gaps - natural;
    const int stretchable = (int)row.size() - (lastIsIndicator ? 1 : 0);
    for (size_t i = 0; i < widths.size(); i++) {
        if (free < 0) {
            widths[i] *= (rowWidth - gaps) / natural;
        } else if ((int)i < stretchable) {
            widths[i] += free / stretchable;
        }
    }
    if (free >= 0 && stretchable == 0) {
        left += free;
    }
    float x = left;
    for (size_t i = 0; i < row.size(); i++) {
        PlaceTab(*row[i], x, y, widths[i], kTabHeight);
        x += widths[i] + kTabGap;
    }
}

uint32_t VisibleColumns() {
    if (!columnArea || columnWidth <= 0) {
        return 0;
    }
    const float scroll = Field<float>(columnArea, kScrollX);
    const float viewport = Field<float>(columnArea, kNodeArea + 8);
    uint32_t visible = 0;
    for (int i = 0; i < (int)tabs.size(); i++) {
        const float left = i * columnWidth + scroll;
        const float shown = (std::min)(left + columnWidth, viewport) - (std::max)(left, 0.0f);
        if (shown >= columnWidth / 2) {
            visible |= 1u << i;
        }
    }
    return visible;
}

void MarkActive(void *screen, int column) {
    if (column < 0 || column >= (int)tabs.size()) {
        return;
    }
    if (shownColumn >= 0 && shownColumn < (int)tabs.size()) {
        SetTabText(tabs[shownColumn], tabLabels[shownColumn]);
    }
    const Tab &tab = tabs[column];
    SetTabText(tab, L"");
    PlaceNode(highlight, tab.x, tab.y, tab.width, tab.height);
    const float textWidth = tabLabels[column].size() * kCharWidthPerFontPixel * tabFontSize;
    PlaceNode(label, tab.x + kTabTextInset - kLabelSlack, tab.y, textWidth + 2 * kLabelSlack, tab.height);
    if (labelText) {
        textFieldSetText(labelText, tabLabels[column].c_str(), 0);
    }
    if (indicator.node) {
        SetTabText(indicator, IndicatorLabel(screen));
    }
}

void MarkVisible(int column, uint32_t visible) {
    for (int i = 0; i < (int)marks.size(); i++) {
        const Tab &tab = tabs[i];
        const bool marked = (visible & (1u << i)) && i != column;
        PlaceNode(marks[i], marked ? tab.x : kHidden, tab.y + tab.height - kMarkHeight, tab.width, kMarkHeight);
    }
}

void RefreshTabs(void *screen) {
    const int column = CurrentColumn(screen);
    const uint32_t visible = VisibleColumns();
    if (column == shownColumn && visible == shownVisible) {
        return;
    }
    if (column != shownColumn) {
        MarkActive(screen, column);
    }
    MarkVisible(column, visible);
    shownColumn = column;
    shownVisible = visible;
}

void BuildTabs(void *screen) {
    activeScreen = screen;
    tabs.clear();
    tabLabels.clear();
    marks.clear();
    highlight = nullptr;
    label = nullptr;
    labelText = nullptr;
    columnArea = nullptr;
    columnWidth = 0;
    shownVisible = 0;
    indicator = Tab{};
    shownColumn = -1;

    uint8_t *list = FindNode(screen, kListNode);
    if (!list) {
        Log("WindowUpper not found; no tabs");
        return;
    }
    const float *listPosition = &Field<float>(list, kNodePosition);
    const float *listArea = &Field<float>(list, kNodeArea);
    const float left = listPosition[0];
    float right = left + listArea[2];
    if (uint8_t *stats = FindNode(screen, kStatsNode)) {
        right = Field<float>(stats, kNodePosition) + Field<float>(stats, kNodeArea + 8);
    }
    const float rowWidth = right - left;
    const float top = listPosition[1] - kListGap - kRows * kTabHeight - (kRows - 1) * kRowGap;

    const int count = CategoryCount(screen);
    if (count <= 0) {
        LogF("no categories (count %d)", Field<int>(screen, kCategoryCount));
        return;
    }
    std::vector<std::wstring> labels;
    for (int i = 0; i < count; i++) {
        labels.push_back(TabLabel(screen, i));
    }
    const std::wstring widestIndicator =
        L"← " + std::to_wstring(count) + L" / " + std::to_wstring(count) + L" →";
    const RowPlan plan = ChooseRows(labels, widestIndicator, rowWidth);
    tabFontSize = plan.fontSize;

    for (int i = 0; i < count; i++) {
        Tab tab = CreateTab(screen);
        if (!tab.node) {
            LogF("couldn't create tab %d", i);
            return;
        }
        tabs.push_back(tab);
    }
    indicator = CreateTab(screen);
    if (!indicator.node) {
        Log("couldn't create the indicator");
        return;
    }

    std::vector<Tab *> firstRow;
    std::vector<Tab *> secondRow;
    std::vector<float> firstWidths;
    std::vector<float> secondWidths;
    for (int i = 0; i < count; i++) {
        (i < plan.split ? firstRow : secondRow).push_back(&tabs[i]);
        (i < plan.split ? firstWidths : secondWidths).push_back(plan.widths[i]);
    }
    secondRow.push_back(&indicator);
    secondWidths.push_back(plan.indicatorWidth);
    PlaceRow(firstRow, firstWidths, left, rowWidth, top, false);
    PlaceRow(secondRow, secondWidths, left, rowWidth, top + kTabHeight + kRowGap, true);

    tabLabels = labels;
    for (int i = 0; i < count; i++) {
        SetTabText(tabs[i], labels[i]);
    }
    for (int i = 0; i < count; i++) {
        marks.push_back(CreateNode(screen, kHighlightTemplate));
    }
    highlight = CreateNode(screen, kHighlightTemplate);
    label = CreateNode(screen, kLabelTemplate);
    labelText = static_cast<uint8_t *>(CastNode(label, kTextFieldTypeRva));
    columnArea = FindNode(screen, kColumnArea);
    if (uint8_t *firstColumn = FindNode(screen, kColumnTemplate)) {
        columnWidth = Field<float>(firstColumn, kNodeArea + 8);
    }
    RefreshTabs(screen);

    LogF("%d tabs in rows of %d + %d, font %.0f, x %.0f-%.0f, y %.0f (columns %lld, current %d)", count,
         plan.split, count - plan.split, plan.fontSize, left, right, top, Field<int64_t>(screen, kColumnCount),
         CurrentColumn(screen));
    for (int i = 0; i < count; i++) {
        LogF("  tab %d: %s at %.0f,%.0f w %.0f", i, Utf8(labels[i]).c_str(), tabs[i].x, tabs[i].y,
             tabs[i].width);
    }
    LogF("  highlight %p, label %p (text field %p), column area %p, column width %.0f", highlight, label, labelText,
         columnArea, columnWidth);
}

bool GameInFront() {
    static ULONGLONG firstCheck = 0;
    static bool seenInFront = false;
    const ULONGLONG now = GetTickCount64();
    if (!firstCheck) {
        firstCheck = now;
    }
    DWORD pid = 0;
    if (HWND window = GetForegroundWindow()) {
        GetWindowThreadProcessId(window, &pid);
    }
    if (pid == GetCurrentProcessId()) {
        seenInFront = true;
        return true;
    }
    return !seenInFront && now - firstCheck > kForegroundGraceMs;
}

bool Pressed(int key, bool &wasDown) {
    const bool down = (GetAsyncKeyState(key) & 0x8000) != 0;
    const bool pressed = down && !wasDown;
    wasDown = down;
    return pressed;
}

struct GameWindowSearch {
    HWND window;
    LONG area;
};

BOOL CALLBACK ConsiderWindow(HWND window, LPARAM param) {
    auto search = reinterpret_cast<GameWindowSearch *>(param);
    DWORD pid = 0;
    GetWindowThreadProcessId(window, &pid);
    RECT client;
    if (pid == GetCurrentProcessId() && IsWindowVisible(window) && GetClientRect(window, &client)) {
        const LONG area = (client.right - client.left) * (client.bottom - client.top);
        if (area > search->area) {
            search->window = window;
            search->area = area;
        }
    }
    return TRUE;
}

bool CursorInUi(float &x, float &y) {
    GameWindowSearch search{nullptr, 0};
    EnumWindows(ConsiderWindow, reinterpret_cast<LPARAM>(&search));
    POINT cursor;
    RECT client;
    if (!search.window || !GetCursorPos(&cursor) || !ScreenToClient(search.window, &cursor) ||
        !GetClientRect(search.window, &client) || client.right <= 0 || client.bottom <= 0) {
        return false;
    }
    const float scaleX = client.right / kUiWidth;
    const float scaleY = client.bottom / kUiHeight;
    const float scale = scaleX < scaleY ? scaleX : scaleY;
    const float offsetX = (client.right - kUiWidth * scale) / 2;
    const float offsetY = (client.bottom - kUiHeight * scale) / 2;
    x = (cursor.x - offsetX) / scale;
    y = (cursor.y - offsetY) / scale;
    return true;
}

int TabUnderCursor() {
    float x = 0;
    float y = 0;
    if (!CursorInUi(x, y)) {
        return -1;
    }
    for (int i = 0; i < (int)tabs.size(); i++) {
        const Tab &tab = tabs[i];
        if (x >= tab.x && x < tab.x + tab.width && y >= tab.y && y < tab.y + tab.height) {
            return i;
        }
    }
    return -1;
}

void JumpToColumn(void *screen, int target) {
    if (ItemCount(screen, target) <= 0) {
        return;
    }
    for (int steps = 0; steps < (int)tabs.size(); steps++) {
        const int current = CurrentColumn(screen);
        if (current == target) {
            return;
        }
        moveColumn(screen, current < target ? kMoveRight : kMoveLeft);
        if (CurrentColumn(screen) == current) {
            return;
        }
    }
}

void HandleInput(void *screen) {
    static bool qDown = false;
    static bool eDown = false;
    static bool clickDown = false;
    const bool inFront = GameInFront();
    const bool previous = Pressed('Q', qDown) && inFront;
    const bool next = Pressed('E', eDown) && inFront;
    const bool click = Pressed(VK_LBUTTON, clickDown) && inFront;
    if (previous) {
        moveColumn(screen, kMoveLeft);
    }
    if (next) {
        moveColumn(screen, kMoveRight);
    }
    if (click) {
        const int tab = TabUnderCursor();
        if (tab >= 0) {
            JumpToColumn(screen, tab);
        }
    }
}

void *__fastcall HookedConstructor(void *screen, void *arg) {
    void *result = originalConstructor(screen, arg);
    BuildTabs(screen);
    return result;
}

void __fastcall HookedInputFrame(void *screen, void *input, float delta) {
    if (screen == activeScreen && !tabs.empty()) {
        HandleInput(screen);
        RefreshTabs(screen);
    }
    originalInputFrame(screen, input, delta);
}

bool Hook(const GameFunction &function, void *detour, void **original) {
    void *target = gameBase + function.rva;
    if (MH_CreateHook(target, detour, original) != MH_OK || MH_EnableHook(target) != MH_OK) {
        LogF("couldn't hook %s", function.name);
        return false;
    }
    return true;
}

void Start() {
    gameBase = reinterpret_cast<uint8_t *>(GetModuleHandleA("EDF.dll"));
    if (!gameBase) {
        Log("EDF.dll isn't loaded; tabs disabled");
        return;
    }
    for (const GameFunction *function :
         {&kConstructor, &kInputFrame, &kMoveColumn, &kInstantiate, &kFindNode, &kSetText, &kTextFieldSetText,
          &kDynamicCast}) {
        if (!MatchesPrologue(*function)) {
            return;
        }
    }
    if (!MatchesTypeName(kComponentTypeRva, kComponentTypeName) ||
        !MatchesTypeName(kButtonTypeRva, kButtonTypeName) ||
        !MatchesTypeName(kTextFieldTypeRva, kTextFieldTypeName)) {
        return;
    }
    moveColumn = reinterpret_cast<MoveColumnFn>(gameBase + kMoveColumn.rva);
    instantiate = reinterpret_cast<InstantiateFn>(gameBase + kInstantiate.rva);
    findNode = reinterpret_cast<FindNodeFn>(gameBase + kFindNode.rva);
    setText = reinterpret_cast<SetTextFn>(gameBase + kSetText.rva);
    dynamicCast = reinterpret_cast<DynamicCastFn>(gameBase + kDynamicCast.rva);
    textFieldSetText = reinterpret_cast<TextFieldSetTextFn>(gameBase + kTextFieldSetText.rva);

    const MH_STATUS init = MH_Initialize();
    if (init != MH_OK && init != MH_ERROR_ALREADY_INITIALIZED) {
        LogF("MH_Initialize failed (%d)", init);
        return;
    }
    if (Hook(kConstructor, reinterpret_cast<void *>(&HookedConstructor),
             reinterpret_cast<void **>(&originalConstructor)) &&
        Hook(kInputFrame, reinterpret_cast<void *>(&HookedInputFrame),
             reinterpret_cast<void **>(&originalInputFrame))) {
        Log("category tabs ready");
    }
}

}

extern "C" BOOL __declspec(dllexport) EML6_Load(PluginInfo *pluginInfo) {
    pluginInfo->infoVersion = PluginInfo::MaxInfoVer;
    pluginInfo->name = "EDF6 UI Tabs";
    pluginInfo->version = PLUG_VER(0, 1, 0, 0);
    static bool started = false;
    if (!started) {
        started = true;
        Start();
    }
    return TRUE;
}

BOOL APIENTRY DllMain(HMODULE module, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(module);
    }
    return TRUE;
}
