const variantClass = {
    primary: "btn-primary",
    ghost: "btn-ghost",
    tonal: "btn-tonal",
    danger: "btn-danger",
}

export default function Button({ variant = "primary", className, children, ...rest }) {
    const classes = ["btn", variantClass[variant] ?? variantClass.primary, className]
        .filter(Boolean)
        .join(" ")
    return (
        <button className={classes} {...rest}>
            {children}
        </button>
    )
}
