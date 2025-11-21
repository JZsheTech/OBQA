import Button from "./Button"

export default function SearchBar({
    value,
    onChange,
    filterValue,
    onFilterChange,
    filterOptions = [],
    onSubmit,
    onReset,
    placeholder,
    loading,
    compact = false,
}) {
    return (
        <form
            className={`search-bar${compact ? " compact" : ""}`}
            onSubmit={(event) => {
                event.preventDefault()
                onSubmit?.()
            }}
        >
            <input
                className="search-bar__input"
                type="text"
                value={value}
                placeholder={placeholder}
                onChange={(event) => onChange?.(event.target.value)}
            />

            {filterOptions.length > 0 && (
                <select
                    className="search-bar__select"
                    value={filterValue}
                    onChange={(event) => onFilterChange?.(event.target.value)}
                >
                    {filterOptions.map((option) => (
                        <option key={option.value} value={option.value}>
                            {option.label}
                        </option>
                    ))}
                </select>
            )}

            <div className="search-bar__actions">
                <Button type="submit" disabled={loading}>
                    {loading ? "搜索中..." : "搜索"}
                </Button>
                {onReset && (
                    <Button type="button" variant="ghost" onClick={onReset}>
                        Reset
                    </Button>
                )}
            </div>
        </form>
    )
}
