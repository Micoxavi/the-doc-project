# Conventions and design criteria

This document defines the main structural criteria used in the project so the repository stays consistent as it grows.

---

## 1. General idea

The project is split into three main concerns:

    1. **Template library**
    2. **Template generation engine**
    3. **Report generation engine**

For it the project directory is divided into different elements:

- **templates**: define the structure of a report
- **components**: define reusable building blocks used inside templates
- **themes**: define visual appearance
- **layouts**: define global page rules
- **python code**: resolves data, applies logic, and renders the final report

The goal is to keep structure, style, layout, and rendering logic separated.

---

## 2. Folder responsibilities

### `templates/base/`
Contains the base structure of a report.

A base template defines:
- report sections
- section order
- which components are used inside each section
- block order inside each section
- block placement rules in that report

---

### `templates/variants/`
Contains derived templates based on a base template.

A variant should only define differences from the base:
- added sections
- removed sections
- renamed sections
- reordered blocks
- small overrides

---

### `templates/components/`
Contains reusable component definitions.

A component defines:
- Block type
- Consumed data
- Internal structure, dimensions and constraints
- fixed labels or titles when they are part of the component identity

The component structure follows this order:

1. Identity.
2. Properties.
   2.1. Content properties.
   2.2. Structural properties.
   2.3. Alignment properties.
   2.4. Row /column contents.

#### Default component behaviour

Unless otherwise specified:

- All defined component parts are rendered.
- Blocks are non-repeatable.
- Structural properties apply the whole component.
- Component-level defaults applied first, and row-level overrides take precedence where defined.

---

### `templates/themes/`
Contains theme definitions.

A theme defines:
- color tokens
- typography tokens
- default styles by component type
- component-specific overrides

A theme controls **appearance**, not structure.

---

### `templates/layouts/`
Contains page-level layout definitions.

A layout defines:
- page size
- orientation
- margins
- reserved header/footer space
- content spacing
- global pagination rules

---

## 3. What belongs where

### Structure of the report
Goes in `base/`

Examples:
- cover
- test section
- appendix
- footer section reference
- order of sections
- order of blocks inside a section

---

### Internal structure of a block
Goes in `components/`

Examples:
- table columns
- row definitions
- fixed block title
- column width ratios
- minimum row height
- internal row types

---

### Visual appearance
Goes in `themes/`

Examples:
- colors
- typography
- default table style
- overrides for specific components

---

### Global page space
Goes in `layouts/`

Examples:
- A4 portrait
- margins
- header height
- footer height
- spacing between blocks

---

### Data-dependent behavior
Handled in Python

Examples:
- paint evaluation cell green if PASS
- paint evaluation cell red if FAIL
- choose whether `results` is rendered as table or chart
- calculate actual width from `width_ratio`

---

