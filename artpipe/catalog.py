"""Read the Unity project's authored data and hand back Descriptors to generate icons for.

Mechanism: Unity `.asset` files are YAML documents with flat scalar fields, and the enum
values inside them are stored as integers. Meaning therefore lives in the C# enum
declarations, so this module parses those too rather than restating them here — rename
`Ice` to `Frost` in C# and the prompts follow with no edit in this file. A hardcoded
int→name table is exactly how the two sides drift apart.

Nothing here interprets the art direction; it produces Descriptors and lets prompt.py
decide whether they are expressible (it raises on Physical, which has no palette entry).

    python3 tools/artpipe/catalog.py            # list every asset and its prompt
    python3 tools/artpipe/catalog.py --json OUT.json
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import prompt as prompt_mod

from project import ROOT as REPO  # gốc project game (ARTPIPE_PROJECT hoặc cwd)
ASSETS = REPO / "Assets"

SPELL_DB = ASSETS / "Settings/Database/SpellDatabase.asset"
STAT_DB = ASSETS / "Settings/Database/StatDatabase.asset"
ITEM_DIR = ASSETS / "Settings/Database/Items"

DAMAGE_TYPE_CS = ASSETS / "Scripts/ECS/Components/DamageType.cs"
SPELL_SUBTYPE_CS = ASSETS / "Scripts/Services/SpellDatabase/SpellSubtype.cs"
ITEM_ENUMS_CS = ASSETS / "Scripts/Core/Items/ItemCategory.cs"


class CatalogError(RuntimeError):
    pass


# ---------------------------------------------------------------- C# enum parsing

_ENUM_BODY = r"enum\s+{name}\b[^{{]*\{{(?P<body>[^}}]*)\}}"
_MEMBER = re.compile(r"^\s*(?P<name>[A-Za-z_]\w*)\s*(?:=\s*(?P<value>\d+)\s*)?,?\s*$")


def parse_enum(cs_path: Path, enum_name: str) -> dict[int, str]:
    """Map value -> member name for one C# enum, honouring implicit increments."""
    text = cs_path.read_text(encoding="utf-8")
    text = re.sub(r"//[^\n]*", "", text)  # comments may contain commas and braces
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    m = re.search(_ENUM_BODY.format(name=re.escape(enum_name)), text)
    if not m:
        raise CatalogError(f"{cs_path}: không tìm thấy 'enum {enum_name}'")

    out: dict[int, str] = {}
    nxt = 0
    for line in m.group("body").splitlines():
        if not line.strip():
            continue
        mm = _MEMBER.match(line)
        if not mm:
            raise CatalogError(f"{cs_path}: không đọc được dòng enum {line.strip()!r}")
        value = int(mm.group("value")) if mm.group("value") else nxt
        out[value] = mm.group("name")
        nxt = value + 1
    if not out:
        raise CatalogError(f"{cs_path}: enum {enum_name} rỗng")
    return out


# ------------------------------------------------------------ Unity asset parsing

@dataclass
class UnityObject:
    fields: dict[str, str]
    anchor: str = ""     # the &-1234 id — several objects share one .asset file

    def get(self, key: str) -> str | None:
        return self.fields.get(key)

    def int_of(self, key: str, default: int | None = None) -> int:
        raw = self.fields.get(key)
        if raw is None:
            if default is None:
                raise CatalogError(f"object {self.fields.get('m_Name')!r} thiếu trường {key!r}")
            return default
        return int(raw)


_DOC_SPLIT = re.compile(r"^--- !u!\d+ &(?P<anchor>\S+)\s*$", re.MULTILINE)
_FIELD = re.compile(r"^  (?P<key>[A-Za-z_]\w*): (?P<value>.*)$", re.MULTILINE)


def read_objects(path: Path) -> list[UnityObject]:
    """Every serialized object in a .asset file, as its top-level scalar fields.

    Deliberately shallow: nested mappings ({fileID: ...}) are kept as their raw text.
    Nothing needed here goes deeper, and a real YAML parse would choke on Unity's tags.
    """
    if not path.exists():
        raise CatalogError(f"không thấy asset: {path}")
    # With a capture group, split() interleaves: [preamble, anchor, body, anchor, body, ...]
    parts = _DOC_SPLIT.split(path.read_text(encoding="utf-8"))
    objects = []
    for anchor, doc in zip(parts[1::2], parts[2::2]):
        fields = {m.group("key"): m.group("value").strip() for m in _FIELD.finditer(doc)}
        if fields:
            objects.append(UnityObject(fields, anchor))
    return objects


def _unescape(value: str) -> str:
    """Unity writes non-ASCII as \\xNN / \\uNNNN inside double-quoted scalars."""
    if value.startswith('"') and value.endswith('"') and len(value) >= 2:
        return value[1:-1].encode("ascii", "backslashreplace").decode("unicode_escape")
    return value


# --------------------------------------------------------------- stat GUID resolution

def _asset_guid_index() -> dict[str, Path]:
    """Unity AssetDatabase GUID -> file path, built from every `.meta` sidecar under Assets/.

    Lets stat_names() chase a `{fileID, guid, type}` reference in StatDatabase.asset back to
    the actual StatDefinitionData asset on disk, the same indirection Unity itself uses —
    without this module having to know or hardcode where stat assets live.
    """
    index: dict[str, Path] = {}
    for meta in ASSETS.rglob("*.meta"):
        m = re.search(r"^guid: ([0-9a-f]{32})\s*$", meta.read_text(encoding="utf-8"), re.MULTILINE)
        if m:
            index[m.group(1)] = meta.with_suffix("")
    return index


def _guid_to_ulong(raw: int) -> int:
    """`BaseDataSO._guidSerialized` is a signed C# long holding the same bits as the ulong
    `Guid` property exposes (Unity cannot serialize ulong directly, see BaseDataSO.cs) — a
    random 64-bit id with its top bit set round-trips through Unity's YAML as a negative
    decimal. Undo that reinterpretation so it compares equal to ModifierData.targetStatGuid,
    which Unity does serialize as an unsigned value directly.
    """
    return raw & 0xFFFFFFFFFFFFFFFF


def stat_names(stat_db_path: Path = STAT_DB) -> dict[int, str]:
    """Map every StatDefinitionData's runtime GUID (BaseDataSO.Guid) to its display name.

    StatType stopped being an enum in the 2026-09-04 migration (see ModifierData.cs) — stats
    are now StatDefinitionData assets identified by GUID, catalogued by StatDatabaseAsset.
    Reading the reference graph instead of restating it here means a new stat asset (e.g. a
    future Relic stat like OrbitCount) needs no change in this file, as long as
    StatDatabaseAsset references it — same reasoning as parse_enum() above.
    """
    if not stat_db_path.exists():
        raise CatalogError(f"không thấy StatDatabase: {stat_db_path}")
    text = stat_db_path.read_text(encoding="utf-8")
    index = _asset_guid_index()

    names: dict[int, str] = {}
    for unity_guid in re.findall(r"guid: ([0-9a-f]{32})", text):
        path = index.get(unity_guid)
        if path is None or not path.exists():
            continue
        for obj in read_objects(path):
            if not (obj.get("m_EditorClassIdentifier") or "").endswith("StatDefinitionData"):
                continue
            guid = _guid_to_ulong(obj.int_of("_guidSerialized"))
            names[guid] = _unescape(obj.get("displayName") or obj.get("m_Name") or "?")
    if not names:
        raise CatalogError(f"{stat_db_path}: không đọc được stat nào")
    return names


# ------------------------------------------------------------------- descriptors

@dataclass
class Entry:
    """A descriptor plus where its finished icon has to be written back to.

    The import step needs three things the prompt step does not care about: which file the
    owning object lives in, which object inside that file it is (a .asset holds many), and
    what the Sprite field is called there — `icon` on spells, `_icon` on items.
    """
    descriptor: prompt_mod.Descriptor
    asset_path: Path
    anchor: str
    object_name: str
    icon_field: str


def spells(db_path: Path = SPELL_DB) -> list[Entry]:
    elements = parse_enum(DAMAGE_TYPE_CS, "DamageType")
    subtypes = parse_enum(SPELL_SUBTYPE_CS, "SpellSubtype")

    out = []
    for obj in read_objects(db_path):
        cls = obj.get("m_EditorClassIdentifier") or ""
        if not cls.endswith("SpellData"):        # SpellData, BeamSpellData; skips ModifierData
            continue
        name = _unescape(obj.get("displayName") or obj.get("m_Name") or "?")
        dt, st = obj.int_of("damageType"), obj.int_of("subtype")
        if dt not in elements:
            raise CatalogError(f"{name}: damageType {dt} không có trong enum DamageType")
        if st not in subtypes:
            raise CatalogError(f"{name}: subtype {st} không có trong enum SpellSubtype")
        out.append(Entry(
            descriptor=prompt_mod.Descriptor(
                kind="spell",
                name=name,
                element=elements[dt],
                subtype=subtypes[st],
                description=_unescape(obj.get("descriptionTemplate") or ""),
            ),
            asset_path=db_path,
            anchor=obj.anchor,
            object_name=obj.get("m_Name") or name,
            icon_field="icon",
        ))
    if not out:
        raise CatalogError(f"{db_path}: không có spell nào")
    return out


def behaviour_modifier_types(scripts: Path | None = None) -> set[str]:
    """Tên kiểu (bỏ hậu tố `ModifierData`) của mọi lớp con `BehaviourModifierData` trong code.

    Modifier hành vi (Pierce, Seeker, ElementShift…) đổi CÁCH spell chạy, không sửa chỉ số
    nào — `targetStatGuid` của chúng bằng 0 là đúng thiết kế. Đọc từ chính mã C# thay vì
    khai danh sách ở đây: thêm một lớp hành vi mới thì catalog tự nhận, còn một modifier chỉ
    số lỡ để trống stat vẫn bị bắt như cũ.
    """
    scripts = scripts or (ASSETS / "Scripts")
    pat = re.compile(r"class\s+(\w+)ModifierData\s*:\s*BehaviourModifierData\b")
    found: set[str] = set()
    for cs in scripts.rglob("*.cs"):
        try:
            found.update(pat.findall(cs.read_text(encoding="utf-8", errors="replace")))
        except OSError:
            continue
    return found


def modifiers(db_path: Path = SPELL_DB) -> list[Entry]:
    """Modifiers live in the same file as the spells, as `ModifierData` objects.

    They carry no element — by design, see art-direction §6b — so the two facts read here
    are which stat they touch and whether they are additive or multiplicative.

    Cách cộng dồn TỪNG LÀ enum `ModifierType`; bản refactor `fa61664` bỏ enum và chuyển nó
    thành lớp con (`Contribute` mỗi lớp tự cộng theo kiểu của nó). Nên ở đây đọc chính TÊN
    LỚP, không đọc enum nữa — và `ModifierData` giờ là abstract nên không asset nào mang
    đúng tên đó.

    Trục stat cũng hết là enum `StatType` cùng đợt migration 2026-09-04 (xem ModifierData.cs
    / stat_names() ở trên) — mỗi ModifierData giờ trỏ `targetStatGuid` tới một
    StatDefinitionData asset, hoặc mang `affectsAllStats` thay cho sentinel `StatType.All` cũ.
    """
    stats = stat_names()
    behaviours = behaviour_modifier_types()

    out = []
    for obj in read_objects(db_path):
        cls = (obj.get("m_EditorClassIdentifier") or "").rsplit(".", 1)[-1]
        if not cls.endswith("ModifierData") or cls == "ModifierData":
            continue
        mod_type = cls[: -len("ModifierData")]
        name = _unescape(obj.get("displayName") or obj.get("m_Name") or "?")
        if mod_type in behaviours:
            # Không có chỉ số để làm trục hình: hình lấy theo chính hành vi
            # (spec `modifier_behaviour_shape`), bố cục theo biến thể `Behaviour`.
            stat_name, mod_type = mod_type, "Behaviour"
        elif obj.int_of("affectsAllStats", 0):
            stat_name = "All"
        else:
            guid = obj.int_of("targetStatGuid", 0)
            if guid not in stats:
                raise CatalogError(f"{name}: targetStatGuid {guid} không khớp stat nào trong StatDatabase")
            stat_name = stats[guid]
        out.append(Entry(
            descriptor=prompt_mod.Descriptor(
                kind="modifier",
                name=name,
                stat=stat_name,
                mod_type=mod_type,
                description=_unescape(obj.get("descriptionTemplate") or ""),
            ),
            asset_path=db_path,
            anchor=obj.anchor,
            object_name=obj.get("m_Name") or name,
            icon_field="icon",
        ))
    if not out:
        raise CatalogError(f"{db_path}: không có modifier nào")
    return out


def items(item_dir: Path = ITEM_DIR) -> list[Entry]:
    categories = parse_enum(ITEM_ENUMS_CS, "ItemCategory")
    rarities = parse_enum(ITEM_ENUMS_CS, "ItemRarity")

    out = []
    for path in sorted(item_dir.glob("*.asset")):
        for obj in read_objects(path):
            if not (obj.get("m_EditorClassIdentifier") or "").endswith("ItemDefinitionAsset"):
                continue
            name = _unescape(obj.get("_displayName") or obj.get("m_Name") or "?")
            cat, rar = obj.int_of("_category", 0), obj.int_of("_rarity", 0)
            if cat not in categories:
                raise CatalogError(f"{name}: _category {cat} không có trong enum ItemCategory")
            if rar not in rarities:
                raise CatalogError(f"{name}: _rarity {rar} không có trong enum ItemRarity")
            out.append(Entry(
                descriptor=prompt_mod.Descriptor(
                    kind="item",
                    name=name,
                    category=categories[cat],
                    rarity=rarities[rar],
                    description=_unescape(obj.get("_description") or ""),
                ),
                asset_path=path,
                anchor=obj.anchor,
                object_name=obj.get("m_Name") or name,
                icon_field="_icon",
            ))
    if not out:
        raise CatalogError(f"{item_dir}: không có item nào")
    return out


def entries() -> list[Entry]:
    return spells() + modifiers() + items()


def entries_from_manifest(path: Path) -> list[Entry]:
    """Icon list from a plain YAML manifest instead of the SKYBORNE game DBs.

    Lets another project (NanoSwarm) drive the same generate/stylise/tier machinery without
    this module knowing its content model. Each item maps 1:1 onto a `prompt.Descriptor`; the
    prompt is still built by `prompt.build`, so a manifest icon is expressed as an existing
    kind (usually `spell`: `element` = palette role, `subtype` = a key in the spec's
    `subtype_shape`). Unity write-back fields are optional — a manifest icon that only needs a
    PNG on disk leaves `asset_path` empty and the import step skips it.

    Manifest shape (either a top-level list, or a mapping with an `icons:` list):

        icons:
          - { kind: spell, name: Energy, element: energy, subtype: energy-cell }
          - { name: Gold Coin, prompt: "a shiny round gold coin with a star", element: gold }
            # không khai kind → kind=spell, tên file = "gold-coin" (không kèm "spell-")
    """
    import yaml

    data = yaml.safe_load(path.read_text("utf-8"))
    items = data["icons"] if isinstance(data, dict) and "icons" in data else data
    if not isinstance(items, list):
        raise CatalogError(f"{path}: manifest phải là list, hoặc mapping có khoá 'icons'")

    out: list[Entry] = []
    for i, it in enumerate(items):
        if "name" not in it:
            raise CatalogError(f"{path}: icon #{i} thiếu 'name'")
        d = prompt_mod.Descriptor(
            kind=it.get("kind", "spell"),
            name=it["name"],
            element=it.get("element"),
            subtype=it.get("subtype"),
            category=it.get("category"),
            rarity=it.get("rarity"),
            stat=it.get("stat"),
            mod_type=it.get("mod_type"),
            description=it.get("description", ""),
            shape_text=it.get("prompt"),
            slug_prefix="kind" in it,
        )
        out.append(Entry(
            descriptor=d,
            asset_path=Path(it["asset_path"]) if it.get("asset_path") else None,
            anchor=it.get("anchor", ""),
            object_name=it.get("object_name", ""),
            icon_field=it.get("icon_field", ""),
        ))
    return out


def all_descriptors() -> list[prompt_mod.Descriptor]:
    return [e.descriptor for e in entries()]


def slug(d: prompt_mod.Descriptor) -> str:
    """Stable output filename stem: kind + name, ascii, lower-kebab."""
    base = re.sub(r"[^A-Za-z0-9]+", "-", d.name).strip("-").lower()
    return f"{d.kind}-{base}" if d.slug_prefix else base


# --------------------------------------------------------------------------- cli

def main() -> int:
    import argparse
    import json
    import sys

    sys.path.insert(0, str(Path(__file__).parent))
    import spec as spec_mod

    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", type=Path,
                    default=REPO / "claude-code-game-studios/design/gdd/art-direction.md")
    ap.add_argument("--json", type=Path, default=None)
    args = ap.parse_args()

    art_spec = spec_mod.load(args.spec)
    records, failed = [], 0
    for d in all_descriptors():
        try:
            text = prompt_mod.build(art_spec, d)
            error = None
        except prompt_mod.PromptError as exc:
            text, error = None, str(exc)
            failed += 1
        records.append({"slug": slug(d), "kind": d.kind, "name": d.name,
                        "element": d.element, "subtype": d.subtype,
                        "category": d.category, "rarity": d.rarity,
                        "stat": d.stat, "mod_type": d.mod_type,
                        "prompt": text, "error": error})
        head = f"{d.kind:5} {d.name}"
        print(f"\033[31mLỖI\033[0m  {head}\n      {error}" if error
              else f"\033[32mOK\033[0m    {head}\n      {text}")

    print(f"\n{len(records) - failed} sẵn sàng · {failed} thiếu dữ liệu")
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(records, indent=2, ensure_ascii=False), "utf-8")
        print(f"ghi {len(records)} bản ghi → {args.json}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
